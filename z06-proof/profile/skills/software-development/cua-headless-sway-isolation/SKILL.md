---
name: cua-headless-sway-isolation
description: Use when Cua tests need Sway input isolation.
---

# Cua headless Sway isolation

Kevin requires Sway for automated GUI/input tests because physical Hyprland has unreliable multi-cursor isolation. This is an input/daemon boundary, not merely a window-placement preference.

1. Halt live tests and stop only confirmed owned host-bound Driver processes when interference is reported. Verify process identity/start time/socket before signaling; verify non-listening afterward. A zombie cannot inject input, but a cached helper may recreate a daemon.
2. Never use global computer_use helpers for these tests: the cached embedded Driver can inherit host HYPRLAND_INSTANCE_SIGNATURE, DISPLAY, WAYLAND_DISPLAY and /run/user runtime. Hermetic lanes remain terminal/files only.
3. Use a separate Sway compositor with WLR_BACKENDS=headless, WLR_RENDERER=pixman, private HOME/XDG_RUNTIME_DIR/Wayland/SWAYSOCK/DBus and no physical input/output devices. Do not use nested WLR_BACKENDS=wayland or Xvfb as an unverified fallback. Fail closed if isolated Sway is unavailable.
4. Reuse the installed user-local Sway at /home/kvn/.local/opt/sway-nested/bin/sway. It requires LD_LIBRARY_PATH=/home/kvn/.local/opt/sway-nested/lib for libwlroots-0.20.so; verify dependencies/version before launching. Do not modify another profile's skill/config or ask for privileged install before checking local artifacts.
5. Enable the actual native input backend with CUA_DRIVER_RS_ENABLE_WAYLAND=1. Without it, pure Wayland input correctly refuses rather than proving input worked. Keep DISPLAY unset and XDG_SESSION_TYPE=wayland so Driver-launched Chromium selects native Wayland.
6. Bind the exact built Driver to an explicit private daemon endpoint. Parent owns serve/start/stop; test wrappers refuse caller socket/direct/embedded overrides and runtime management operations. Never attach the user's resident daemon.
7. Account for MCP environment allowlists: jev-use forwards desktop fields and CUA_DRIVER_* but omits SWAYSOCK, WLR_BACKENDS, LD_LIBRARY_PATH and CUA_SWAY_LEASE. Restore these only from the parent's private-runtime lease in the evidence wrapper, including the marker so teardown finds proxy clients. Do not change shipped runner policy just to repair the test harness.
8. Reject host Hyprland/DISPLAY/injection/DBus routes and escaped lease paths before Driver exec. Exercise endpoint corruption and host-routing negative controls; an empty success flag is not isolation evidence.
9. Record independent Sway IPC version/HEADLESS output/input-device facts, owned daemon/process environments and before/after sanitized physical host focus. Check owned process/socket/runtime absence on teardown and cancellation. Never focus the host to inspect a test.
10. Treat move_cursor effect=unverifiable as delivery acknowledgment, not an independent cursor-position oracle. A passing isolation receipt does not establish the experiment's semantic outcome; retain fixture state/journal separately for optimization evidence.
11. Treat the existing evidence-local harness as NOT resume-certified until its independent review blockers are fixed and re-audited. Basic smoke/refusal success is insufficient: cancellation can bypass cleanup, environment-marker scans miss filtered descendants, and unbound leases can pass admission.
12. Protect setup through teardown with an outer lifetime finally; make teardown resistant to repeated cancellation, restore signal handlers unconditionally, bound every startup/IPC wait, and test failures around every process launch plus filtered descendants. Use stable process identities and lifetime ownership that survives environment scrubbing; marker matching alone is not ownership.
13. Reject endpoint symlinks and escaped paths, require actual listening private sockets, and validate the entire DBus address rather than a prefix before forwarding it. Scrub or explicitly constrain the system bus. Bind distinct owner executable/start identities and socket peers to a parent-established verified binary lease; state that trusted same-UID environment routing is not an OS sandbox.
14. Allowlist audited wrapper operations and reject ownership switches across the complete argument vector. Prove endpoint loss cannot select a default/global daemon or direct-input fallback; never infer fail-closed routing from a short denylist.

Evidence-local harness: /mnt/zer0models/github/cua-lanes/speed-frontier/research/work-deletion/isolation/sway_session.py. private_driver.py restores the private lease and binds its endpoint; sway_isolation.py rejects host routes. Reproduce with an absolute new --receipt path and `-- COMMAND`. Preserve failed receipts and re-run after code/hash changes. Independent safety review is required before broader live measurement resumes.
