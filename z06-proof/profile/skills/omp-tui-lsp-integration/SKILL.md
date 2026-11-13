---
name: omp-tui-lsp-integration
class: integration
description: Configure Hermes to reuse OMP's LSP via multiplexer.
version: 1
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: ["lsp", "integration", "omp-tui"]
    related_skills: []
---
# omp-tui-lsp-integration

## When to Use
Use when you want Hermes agent to attach to the existing OMP LSP multiplexer, avoiding duplicate language‑server spawns and sharing workspace state with the OMP TUI.

## Procedure

1. **Ensure the OMP LSP multiplexer socket is exported**
   - In the environment where Hermes agent runs, set:
     ```bash
     export OMP_LSP_MUX_SOCKET=/path/to/omp/lsp/mux.socket
     ```
   - The socket is typically created by OMP when its LSP is started (see OMP docs).

2. **Verify Hermes agent detects the socket**
   - Hermes agent’s LSP manager checks `mux_socket()` (from `agent/lsp/omp_mux.py`).
   - If the variable is empty or the socket does not exist, Hermes falls back to spawning its own LSP binary.

3. **Let Hermes agent request the server command from the mux**
   - The manager calls `omp_server_command(cwd, extension)` via the mux’s `omp/serverForFile` method.
   - The mux returns the command and arguments OMP would use for the given file extension (e.g., `pyright` for `.py`).

4. **Attach to the mux‑provided server**
   - The LSP client invokes `attach_omp_mux(cmd, cwd)` (see `agent/lsp/client.py`).
   - This performs a Unix‑domain socket connection to the mux and sends an `omp/muxConnect` request with the command, args, and cwd.
   - The mux replies with a socket‑pair (`MuxProc`) that mimics a subprocess’s stdin/stdout/stderr.

5. **Proceed with normal LSP client lifecycle**
   - From this point, the client treats the `MuxProc` as the server process:
     * Starts reader and stderr‑drain tasks.
     * Sends `initialize`, `initialized`, and subsequent LSP requests/notifications.
     * All diagnostics, completions, and workspace‑folder notifications flow through the multiplexer to OMP’s actual language server.

## Pitfalls

- **Do not set `OMP_LSP_MUX_SOCKET` to a non‑socket path** – the manager will treat it as set, but `asyncio.open_unix_connection` will fail with `LSPProtocolError: OMP LSP mux socket is not set`. Ensure the variable points to an existing Unix domain socket.
- **If the mux does not support the requested language**, `omp_server_command` returns `None` and Hermes logs an "OMP LSP mux" unavailable event. In that case, Hermes will fall back to spawning its own server (if the binary is available). Verify that OMP’s mux is configured for the languages you need.
- **The mux‑provided `MuxProc` has `stderr = None`** – the LSP client’s stderr‑drain task will see no data; rely on the mux’s own logging or OMP’s server stderr for diagnostics.
- **Environment inheritance** – when attaching via the mux, the client does **not** receive the delegated child subprocess environment (no scrubbed gateway tokens). The mux‑server inherits the environment of the OMP process, not Hermes agent’s delegated env. If your language server expects Hermes‑specific env vars, set them in the OMP process environment before starting the mux.

## Verification

- Check the agent log for lines like:
  ```
  [lsp] Attaching to OMP mux socket at <path>
  [lsp] Server command resolved: <command> <args>
  ```
- Confirm that no new language‑server process appears in the process list for the same language; instead, you see the existing OMP server PID reused.

## References

- See `agent/lsp/omp_mux.py` for the multiplexer protocol details.
- See `agent/lsp/manager.py` (around the `if mux_socket():` block) for integration point.
- See `agent/lsp/client.py` (`_spawn` method) for the attach call.
