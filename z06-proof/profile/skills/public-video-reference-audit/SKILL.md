---
name: public-video-reference-audit
description: "Use when auditing video references or planning X launches."
---
# Public video reference audit

## Procedure for interaction demos

1. **Acquire the primary media before advising.** For a linked interaction demo, download the exact clip and verify its audio/video streams and duration with ffprobe. Treat search-model descriptions as discovery only. If primary media remains inaccessible, state that boundary instead of building a confident interaction plan from a summary.
2. **Inspect the whole temporal sequence.** For a short UI demo, begin with chronological half-second samples from start through the final frame, then enlarge controls, submission transitions and ambiguous actions. Increase temporal sampling around each unresolved action; half-second coverage is a discovery pass, not proof that every brief interaction was captured. Track cursor movement, ink, playback state, frame stepping, recording state and sidebar changes separately. Sparse hero frames are insufficient when the user asks for every interaction. Use the denser extraction recipe in `references/interaction-video-analysis.md`, and state the sampling boundary rather than claiming literal continuous viewing.
3. **Process speech independently.** Transcribe the complete audio track and align it with visible actions; compare wording with any on-screen summary. Do not claim to have listened when using speech recognition, or treat polished sidebar text as a verbatim transcript. Use the working offloaded Whisper recipe in the reference when appropriate.
4. **Separate the clocks and actors.** Distinguish elapsed demo time, the reviewed artifact's playhead and the feedback recording duration. Separate the reviewer's real cursor from pointers animated inside the artifact; otherwise playback can be mistaken for a user action.
5. **Report observations before interpretation.** When asked for all interactions, answer with the chronological walkthrough, short speech excerpts and visible results—not another implementation proposal. Identify hidden triggers as unknown: a tooltip proves an available shortcut, not which key was pressed; a submitted card proves submission, not an unseen Send click. When adapting the demo to another product, preserve its demonstrated interaction first and identify the actual missing behavior; do not replace continuous creative direction with a generic bug-reporting, telemetry or regression-testing roadmap.
6. **Bound capability and outcome claims.** Say exactly whether evidence came from sampled frames, native video processing or audio transcription. An agent acknowledgment is not an implemented edit; require a visible changed artifact before claiming the demo closes the loop. Treat animated keystroke overlays, edited time jumps and completion counters as demonstrations, not raw input logs, measured latency or verified throughput. Identify reused launch footage among README animations so several files do not imply independent confirmations.
7. **Corroborate source-backed UX at an exact revision.** For adaptation requests, inspect the implementation as well as the demo before recommending changes. Report revision drift and conflicts between current code and older product copy explicitly; keep demonstrated behavior, implementation findings and proposed adaptation separate.

## Planning a launch-video series for the owner's work on X

Use this when the owner asks what he has posted, which formats work for him, or how to make his feature demos go viral.
1. **Read his own history first** with agent-reach's `twitter user-posts _kvnloo -n 200 --json` (handle `_kvnloo`). Split authored posts from retweets. Compute per-format medians (text / photo / video / link) and list the top posts with their captions. Then read his older videos individually with `twitter tweet <id>`, because the 200-item window misses older launch clips.
2. **Mine his retweeted videos as a taste swipe file.** They are references he already picked, with exact views and `video.twimg.com` URLs you can ffprobe. Hand that file to every researcher so case studies are grounded in his taste and in verified numbers rather than web folklore.
3. **Fan out along fixed slices** (see token-thrifty-agent-routing for the billing gate):
   - viral case studies and format archetypes (paid model)
   - X ranking and distribution, plus a growth playbook against his baseline (paid model)
   - production pipeline and craft on his Linux setup (paid model)
   - surveys of the tool category and of the target ecosystem's accounts (free lane is fine)

   Every brief carries: the feature list, his follower baseline, read-only use of X, "never fabricate URLs/numbers, mark unverified", and an absolute report path under the project's kitchen dir (`.../kitchen/<project>-<date>/x-research/NN-<slice>.md`).
4. **Spot-check before relaying.** Re-read at least one headline metric yourself with `twitter tweet <id>`. Label free-lane reports as unverified leads.
5. **Write `SYNTHESIS.md`** with these sections: his own signal table, open gaps in the ecosystem, which format fits which feature, distribution facts labeled as code-backed or folklore, the production recipe, a dated plan, then gaps. Reply in the same order, keeping it short.

Standing defaults and findings for this owner are in `references/x-launch-series-playbook.md`. Re-verify the numbers there before quoting them as current.

## Additional audit rules

- Verify handles from the creator's official link hub; educational and entertainment accounts may differ.
- Enumerate videos and shorts separately with `yt-dlp --flat-playlist -J`; persist and sort in Python. Flat-list views may be rounded. Fetch individual selected items with `--skip-download -J` for views, likes and dates; retain nulls.
- For read-only X research on the owner's host, prefer logged-in `twitter tweet <id> --json`; it returns the target plus thread/replies, so select the exact ID rather than taking the largest count. `twitter user-posts <handle> -n 200 --json` includes retweets; filter `isRetweet`, author and replies before computing a baseline. Do not use the broken `twitter search` path. Run this CLI through the host terminal: a tool's Python sandbox may have a different HOME/auth environment. Never inspect cookies to bridge that difference.
- Preserve successful snapshots separately from error responses; a retry returning 429 must not overwrite the only successful timeline. Bound retries and serialize large timeline requests when rate-limited. Treat a capped recent timeline as a current sample, not a historical launch baseline; current follower counts are not followers at posting time.
- A video with an audio stream is not necessarily narrated, and empty speech recognition is not proof of silence or music. Report no-audio streams as silent; report ASR-positive speech as machine-transcribed rather than personally heard; retain music as unverified unless independently auditioned.
- Try public yt-dlp without cookies when generic web extraction rejects Instagram, TikTok or X. Record checked dates and raw metadata. X video plays are not necessarily post impressions.
- For an exact X video, public `https://api.fxtwitter.com/<handle>/status/<id>` can expose media variants. If a video.twimg.com variant returns 403, bound retries and try another listed MP4 with curl, a browser user-agent and X Referer; a variant without the `?tag=` query may work. Verify duration with ffprobe and inspect chronological frames before proposing interaction designs. A model-generated X/video summary is secondary evidence, not having watched the clip; do not turn it into a confident product plan.
- Verify every completed download with ffprobe: video stream, expected duration and nonzero bytes. Do not select `.part`, intermediate `.f401.mp4`, or empty files as finished references. A downloader can print success for an empty file.
- Bound 403 retries. An accessible creator-posted counterpart on another platform is useful but must retain its own URL and metrics, never impersonate the original download.
- For editorial/popularity analysis, inspect opening-second frames, distributed frames and the ending; for interaction analysis, use the denser full-sequence procedure above. Keep downloads private, not published assets.
- Describe ffmpeg `scene > 0.30` as candidate segments, not manual editorial shots. Letterbox and static overlays hide cuts; flashes and camera shakes create false cuts. Preserve parameters and cut times.
- Check for 360 projections: a 16:9 encoded file does not necessarily have a widescreen viewing composition.
- Budget long 4K HLS downloads separately from short clips; inspect fragment progress, preserve resumable parts, and resume only after the prior process exits. A short wrapper timeout can kill a healthy nearly-complete download.
- Verify public discussion dates from their API timestamps rather than recollection; distinguish repository creation, early demos, promised releases and the actual published launch.
- Check existing analysis files before declaring a downloaded count: a contact sheet alone does not prove the original video survived download or that its scene pass completed.
- Separate measurements, visual observations and hypotheses about popularity. Do not infer retention or causal effects from views.
- Do not infer music genre or BPM from stills. Record available soundtrack metadata and mark listening/BPM unverified when unauditioned.
- Review media licensing independently of code licensing: MIT repositories may forbid standalone reuse of their promotional GIFs.
