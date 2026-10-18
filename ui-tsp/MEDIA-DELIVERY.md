# Media across hosts

Local files retain the existing `media.path` / `image.path` fast path. Paths are
not portable: the renderer distinguishes the Tern host, frontend process,
gateway, and session compute backend. An attached WebSocket gateway or an SSH
frontend is not assumed to share Tern's filesystem. SSH environment markers
(`SSH_CONNECTION`, `SSH_CLIENT`, `SSH_TTY`) conservatively disable the path fast
path. A separate non-local terminal backend's files are never read from an
identically named gateway/frontend path.

Cross-host image chips offer **Load image preview**. Completed `read_file` and
browser screenshot cards use the same delivery boundary. Loading is explicit,
not a render side effect; failures remain visible with **Retry preview**.

- Frontend-owned paths are opened as regular files, with bounded reads.
- Gateway paths use `media.image`, authorized against the owning transport's
  session, staged/persisted `@image:` attachments or exact completed tool call.
  Session authority is checked again after reading. No client-provided arbitrary
  path becomes authority, and non-local compute backend paths are refused.
- The file's actual format must be a supported raster image, and a declared MIME
  must agree with its magic bytes. Filename extensions cannot establish format.
- Bytes go through the negotiated `Session.blob(bytes, mime)` API; image nodes
  reference the SDK's content-addressed ID, never a made-up ID or encoder.
- Persisted attachment path IDs survive resume. Blob IDs are presentation-only,
  never stored in Hermes history. Old pending reads/actions are discarded on
  removal, session adoption, or quit.

## Bounds and lifetime

The SDK's current blob maximum is **16 MiB per preview**. One preview transfer
runs at a time, with **32 cached metadata entries** (insertion-order eviction).
Image buffers/base64 responses are not retained in the cache or transcript;
only the resulting SDK ID and status remain. Eviction returns a preview to its
explicit load action, not an automatic retry loop.

SDK 0.1 deduplicates uploads for the connection and has **no release/re-upload
API**. The frontend therefore bounds preview uploads cumulatively to **64 calls
and 64 MiB per SDK connection**, including reloads and session changes. Clearing
a view/session does not reset these budgets. Budget exhaustion asks for a
reconnect; it never fabricates an upload. Terminal-side reclamation/eviction is
owned by Tern, not promised by this cache; if the peer discards a previously sent
blob, reconnect is required with SDK 0.1. The application does not implement a
second terminal cache or an encoder to bypass that limitation.

Composer staging is separately capped at **8 images** and **40 MiB of retained
base64 payload** (encoded-length admission), with the existing 20 MiB per-image
upload limit. Confirmed uploads discard the original in-memory payload and keep
a fingerprint for deduplication. A local frontend file targeting a remote
gateway uses `image.attach_bytes`, never the frontend's path on that gateway.
A terminal-host drop path across SSH is refused with guidance to paste image
bytes instead.

## Explicitly unsupported / evidence

Remote video, audio, PDF and 3D previews are not asserted to support blobs. They
retain a visible unsupported state; local native media behavior is unchanged.
Separate compute-host SSH/container media transfer and peer blob-release/
eviction recovery are not negotiated by the installed SDK and are not claimed.
The application adds no polling loops or idle timers.

The ownership and negotiated-blob model was checked against OMP (Can Bölük /
Stencil, MIT), pinned `eb74cf84`, `packages/tui/src/native/backend.ts:656–708` and
`native/blobs.ts:82–135`. No OMP encoder/cache code is copied; Tern's SDK owns the
wire. Unit journeys mount the real App/SDK against a fixture gateway and inspect
emitted trees. Live signed-in remote Tern/SSH media remains a separate manual
qualification, not implied by fixture or tern-serve receipts.
