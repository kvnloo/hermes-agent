// burstcap: record a burst of compositor frames from one Wayland output into a
// raw file, with the compositor's own timestamp for every frame.
//
// It speaks wlr-screencopy (Hyprland, Sway, wlroots), so it needs no root, no
// portal prompt and no encoder in the loop: the compositor writes each frame
// straight into shared memory this program never touches, and the frames are
// written out and encoded afterwards. That keeps the capture path as short as
// the protocol allows and makes it a measuring instrument: the timestamp log
// says how many frames the compositor really delivered, and when. It holds
// the whole burst in RAM, so size the burst (-n) to fit.
//
//   burstcap -o OUTPUT [-g X,Y,W,H] [-n FRAMES] [-t SECONDS] [-a] [-s] -f frames.raw
//
//   -o  output name (hyprctl monitors)
//   -g  region of the output, in output pixels (default: all of it)
//   -n  stop after this many frames (default 1080)
//   -t  stop after this many seconds (default 10)
//   -a  take every compositor frame; default waits for damage, so a frame is
//       only delivered when something on the output changed
//   -s  stream: write each frame to stdout as it arrives instead of holding
//       the burst in RAM, for takes too long to hold (pipe it to an encoder;
//       -f then only names the .json and .times files). Fine at 60 fps, not
//       a way to go faster: the copy to the pipe is in the loop.
//
// Writes FILE (BGRx/XRGB8888-style rows, as the compositor gives them),
// FILE.json (size, format, counts) and FILE.times (one line per frame:
// index, seconds, damaged flag).

#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/sendfile.h>
#include <time.h>
#include <unistd.h>
#include <wayland-client.h>

#include "wlr-screencopy-unstable-v1-client-protocol.h"

struct output {
	struct wl_output *wl;
	char name[64];
	struct output *next;
};

static struct wl_shm *shm;
static struct zwlr_screencopy_manager_v1 *manager;
static struct output *outputs;

static struct {
	uint32_t format, width, height, stride;
	bool known;
} geo;

// Frames live in memfd-backed pools (a wl_shm pool is capped at 2 GiB), one
// wl_buffer per frame, so nothing is copied on this side during the burst.
#define POOL_BYTES ((size_t)1 << 30)
static size_t frame_bytes, pool_frames;
static int pool_fds[4096];
static struct wl_shm_pool *pools[4096];
static uint32_t pool_count;

static double *stamps;
static uint8_t *damaged;
static uint32_t frames, max_frames = 1080;
static bool frame_done, frame_failed, frame_damaged, buffer_ready;
static double frame_time;

static void output_geometry(void *d, struct wl_output *o, int32_t x, int32_t y, int32_t pw, int32_t ph, int32_t sp,
                            const char *make, const char *model, int32_t tr) {}
static void output_mode(void *d, struct wl_output *o, uint32_t f, int32_t w, int32_t h, int32_t r) {}
static void output_done(void *d, struct wl_output *o) {}
static void output_scale(void *d, struct wl_output *o, int32_t s) {}
static void output_name(void *d, struct wl_output *o, const char *name) {
	snprintf(((struct output *)d)->name, sizeof ((struct output *)d)->name, "%s", name);
}
static void output_description(void *d, struct wl_output *o, const char *desc) {}

static const struct wl_output_listener output_listener = {
	output_geometry, output_mode, output_done, output_scale, output_name, output_description,
};

static void registry_global(void *d, struct wl_registry *r, uint32_t id, const char *iface, uint32_t ver) {
	if (!strcmp(iface, wl_shm_interface.name)) {
		shm = wl_registry_bind(r, id, &wl_shm_interface, 1);
	} else if (!strcmp(iface, zwlr_screencopy_manager_v1_interface.name)) {
		manager = wl_registry_bind(r, id, &zwlr_screencopy_manager_v1_interface, ver < 3 ? ver : 3);
	} else if (!strcmp(iface, wl_output_interface.name) && ver >= 4) {
		struct output *o = calloc(1, sizeof *o);
		o->wl = wl_registry_bind(r, id, &wl_output_interface, 4);
		wl_output_add_listener(o->wl, &output_listener, o);
		o->next = outputs;
		outputs = o;
	}
}
static void registry_remove(void *d, struct wl_registry *r, uint32_t id) {}
static const struct wl_registry_listener registry_listener = {registry_global, registry_remove};

static struct wl_buffer *frame_slot(uint32_t index) {
	uint32_t p = index / pool_frames;
	if (p >= pool_count) {
		int fd = memfd_create("burstcap", MFD_CLOEXEC);
		size_t bytes = pool_frames * frame_bytes;
		// Fault the pages in now, not while the compositor is writing a frame.
		if (fd < 0 || ftruncate(fd, bytes) < 0 || posix_fallocate(fd, 0, bytes) != 0) {
			perror("burstcap: frame memory");
			exit(1);
		}
		pool_fds[p] = fd;
		pools[p] = wl_shm_create_pool(shm, fd, bytes);
		pool_count = p + 1;
	}
	return wl_shm_pool_create_buffer(pools[p], (index % pool_frames) * frame_bytes, geo.width, geo.height, geo.stride,
	                                 geo.format);
}

static void frame_buffer(void *d, struct zwlr_screencopy_frame_v1 *f, uint32_t format, uint32_t w, uint32_t h,
                         uint32_t stride) {
	if (!geo.known) {
		geo.format = format;
		geo.width = w;
		geo.height = h;
		geo.stride = stride;
		geo.known = true;
	} else if (geo.width != w || geo.height != h || geo.stride != stride) {
		fprintf(stderr, "burstcap: the output changed size mid-capture\n");
		frame_failed = true;
	}
	buffer_ready = true;
}
static void frame_flags(void *d, struct zwlr_screencopy_frame_v1 *f, uint32_t flags) {}
static void frame_ready(void *d, struct zwlr_screencopy_frame_v1 *f, uint32_t hi, uint32_t lo, uint32_t nsec) {
	frame_time = (double)(((uint64_t)hi << 32) | lo) + nsec / 1e9;
	frame_done = true;
}
static void frame_failed_cb(void *d, struct zwlr_screencopy_frame_v1 *f) {
	frame_failed = true;
}
static void frame_damage(void *d, struct zwlr_screencopy_frame_v1 *f, uint32_t x, uint32_t y, uint32_t w, uint32_t h) {
	if (w && h) {
		frame_damaged = true;
	}
}
static void frame_dmabuf(void *d, struct zwlr_screencopy_frame_v1 *f, uint32_t format, uint32_t w, uint32_t h) {}
static void frame_buffer_done(void *d, struct zwlr_screencopy_frame_v1 *f) {}

static const struct zwlr_screencopy_frame_v1_listener frame_listener = {
	frame_buffer, frame_flags, frame_ready, frame_failed_cb, frame_damage, frame_dmabuf, frame_buffer_done,
};

static double now(void) {
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return ts.tv_sec + ts.tv_nsec / 1e9;
}

int main(int argc, char **argv) {
	const char *want = NULL, *path = NULL;
	int rx = 0, ry = 0, rw = 0, rh = 0, opt;
	double seconds = 10;
	bool every = false, stream = false;
	struct wl_buffer *stream_buffer = NULL;
	void *stream_data = NULL;

	while ((opt = getopt(argc, argv, "o:g:n:t:asf:")) != -1) {
		switch (opt) {
		case 'o': want = optarg; break;
		case 'g':
			if (sscanf(optarg, "%d,%d,%d,%d", &rx, &ry, &rw, &rh) != 4) {
				fprintf(stderr, "burstcap: -g takes X,Y,W,H\n");
				return 2;
			}
			break;
		case 'n': max_frames = strtoul(optarg, NULL, 10); break;
		case 't': seconds = atof(optarg); break;
		case 'a': every = true; break;
		case 's': stream = true; break;
		case 'f': path = optarg; break;
		default: return 2;
		}
	}
	if (!want || !path) {
		fprintf(stderr, "usage: burstcap -o OUTPUT [-g X,Y,W,H] [-n FRAMES] [-t SECONDS] [-a] -f FILE\n");
		return 2;
	}

	struct wl_display *display = wl_display_connect(NULL);
	if (!display) {
		fprintf(stderr, "burstcap: no Wayland display\n");
		return 1;
	}
	struct wl_registry *registry = wl_display_get_registry(display);
	wl_registry_add_listener(registry, &registry_listener, NULL);
	wl_display_roundtrip(display);
	wl_display_roundtrip(display);

	struct wl_output *target = NULL;
	for (struct output *o = outputs; o; o = o->next) {
		if (!strcmp(o->name, want)) {
			target = o->wl;
		}
	}
	if (!shm || !manager || !target) {
		fprintf(stderr, "burstcap: %s\n", !manager ? "the compositor has no wlr-screencopy" : "no such output");
		return 1;
	}

	int fd = -1;
	double started = 0, deadline = 0;
	uint32_t undamaged = 0;

	while (frames < max_frames) {
		struct zwlr_screencopy_frame_v1 *frame =
			rw ? zwlr_screencopy_manager_v1_capture_output_region(manager, 0, target, rx, ry, rw, rh)
			   : zwlr_screencopy_manager_v1_capture_output(manager, 0, target);
		zwlr_screencopy_frame_v1_add_listener(frame, &frame_listener, NULL);
		frame_done = frame_failed = frame_damaged = buffer_ready = false;

		while (!buffer_ready && !frame_failed && wl_display_dispatch(display) != -1) {}
		if (frame_failed) {
			fprintf(stderr, "burstcap: the compositor refused the capture\n");
			return 1;
		}

		if (!stamps) {
			frame_bytes = (size_t)geo.stride * geo.height;
			pool_frames = POOL_BYTES / frame_bytes ? POOL_BYTES / frame_bytes : 1;
			if (stream) {
				// One buffer, reused: each frame goes straight down the pipe.
				int sfd = memfd_create("burstcap", MFD_CLOEXEC);
				if (sfd < 0 || ftruncate(sfd, frame_bytes) < 0) {
					perror("burstcap: frame memory");
					return 1;
				}
				stream_data = mmap(NULL, frame_bytes, PROT_READ, MAP_SHARED, sfd, 0);
				struct wl_shm_pool *pool = wl_shm_create_pool(shm, sfd, frame_bytes);
				stream_buffer = wl_shm_pool_create_buffer(pool, 0, geo.width, geo.height, geo.stride, geo.format);
				wl_shm_pool_destroy(pool);
				close(sfd);
			}
			// Reserve every pool before the clock starts.
			for (uint32_t i = 0; !stream && i < max_frames; i += pool_frames) {
				wl_buffer_destroy(frame_slot(i));
			}
			wl_display_roundtrip(display);
			stamps = calloc(max_frames, sizeof *stamps);
			damaged = calloc(max_frames, 1);
			started = now();
			deadline = started + seconds;
		}

		struct wl_buffer *buffer = stream ? stream_buffer : frame_slot(frames);
		if (every) {
			zwlr_screencopy_frame_v1_copy(frame, buffer);
		} else {
			zwlr_screencopy_frame_v1_copy_with_damage(frame, buffer);
		}
		while (!frame_done && !frame_failed && wl_display_dispatch(display) != -1) {}
		zwlr_screencopy_frame_v1_destroy(frame);
		if (!stream) {
			wl_buffer_destroy(buffer);
		}
		if (frame_failed) {
			break;
		}
		if (stream) {
			const uint8_t *at = stream_data;
			size_t left = frame_bytes;
			while (left) {
				ssize_t sent = write(STDOUT_FILENO, at, left);
				if (sent <= 0) {
					perror("burstcap: writing to the pipe");
					return 1;
				}
				at += sent;
				left -= sent;
			}
		}

		stamps[frames] = frame_time;
		damaged[frames] = frame_damaged || every;
		undamaged += !frame_damaged;
		frames++;

		if (now() >= deadline) {
			break;
		}
	}

	double wall = now() - started;

	// The burst is over: write the frames out, pool by pool.
	fd = stream ? -1 : open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
	if (fd < 0 && !stream) {
		perror("burstcap: output file");
		return 1;
	}
	for (uint32_t p = 0, left = frames; !stream && p < pool_count && left; p++) {
		uint32_t n = left < pool_frames ? left : pool_frames;
		off_t at = 0;
		size_t bytes = (size_t)n * frame_bytes;
		while (bytes) {
			ssize_t sent = sendfile(fd, pool_fds[p], &at, bytes);
			if (sent <= 0) {
				perror("burstcap: writing frames");
				return 1;
			}
			bytes -= sent;
		}
		close(pool_fds[p]);
		left -= n;
	}
	close(fd);

	char side[4096];
	snprintf(side, sizeof side, "%s.times", path);
	FILE *t = fopen(side, "w");
	for (uint32_t i = 0; t && i < frames; i++) {
		fprintf(t, "%u %.9f %d\n", i, stamps[i], damaged[i]);
	}
	if (t) {
		fclose(t);
	}
	snprintf(side, sizeof side, "%s.json", path);
	FILE *j = fopen(side, "w");
	if (j) {
		fprintf(j,
		        "{\"output\":\"%s\",\"width\":%u,\"height\":%u,\"stride\":%u,\"wl_shm_format\":%u,"
		        "\"frames\":%u,\"wall_seconds\":%.6f,\"every_frame\":%s,\"no_damage_frames\":%u}\n",
		        want, geo.width, geo.height, geo.stride, geo.format, frames, wall, every ? "true" : "false", undamaged);
		fclose(j);
	}
	fprintf(stderr, "burstcap: %u frames of %ux%u in %.3fs (%.1f fps) -> %s\n", frames, geo.width, geo.height, wall,
	        wall > 0 ? frames / wall : 0, path);
	return frames ? 0 : 1;
}
