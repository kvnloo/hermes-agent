# Confirmed write figures

Successful `write_file` cards lead with a native SVG/Mermaid fence or a negotiated
model media node. Source, any existing diff, diagnostics and the file target stay
underneath. A figure disables the ordinary code-line preview clamp; folding the
card remains a presentation-only user action.

## Confirmation and identity

`confirmedWriteArtifact` projects the owning `ToolCall` on each changed transcript
revision. It requires a completed call, `WriteResult.verified === true` (the file
backend's on-disk hash verification), no error/partial/truncation, and an exact
UTF-8 `bytes_written` match to the completed call's source. Arguments alone,
legacy results lacking verification, and differently sized partial source do not
produce a figure. These cases retain the ordinary source/diff presentation.
BOM/line-ending normalization that changes the byte count also falls back rather
than claiming an exact source match.

The figure key incorporates the call id, resolved path, source and current result.
Replacing a completion removes or remounts its figure without an async preview
cache. This key is **not** the SDK media node's `rev`, which exclusively names a
git revision. Path-backed models display the current host file; this does not
create an immutable historical snapshot or a second artifact store.

## Paths and formats

- The result's `resolved_path` wins over the requested path; relative paths resolve
  against the owning session's cwd, never the pane/process cwd.
- Host-local model viewers and file links require both a non-attached gateway and
  the session's explicit `terminal_backend: local`. Attached gateways (including
  loopback), SSH, container and unknown backends are not assumed to share files.
  They retain a labelled path, source and diagnostics, but no misleading local
  file link or model viewer. Confirmed inline SVG/Mermaid source still renders.
- SVG, `.mmd` and `.mermaid` use the native Markdown fence renderer and
  `omp.tool.write.figure` role; native theme changes require no hardcoded colors.
  Source fence delimiters are escaped by choosing a longer enclosing fence.
- Models reuse the existing media adapter and negotiated `caps.kinds` support.
  Without `media`, the card keeps its source and host-local file link.
- Contradictory reported MIME types suppress the figure. Model MIME matching is
  extension-specific (a `model/obj` result is not a confirmed GLB).
- Generated JS/Luau are never evaluated or promoted to executable nodes. This
  feature is independent of `/visual` generation.

## Verification

`src/__tests__/render-written-svg-mermaid.test.ts` mounts the real SDK App with a
fake gateway, including live/resume, completion replacement, path locality,
capability absence, theme events, MIME disagreement and failure/partial cases.

The owned `written-artifacts` E2E journey writes and reads actual SVG/Mermaid
source files, then **explicitly fixture-replays** their completed-write events.
It checks figure/source order and failed-write status and captures the renderer.
This is not an agent/model write or proof of a remote model transfer. The runner
keeps signed-out ordinary-window blocks separate from `tern-serve` evidence.
