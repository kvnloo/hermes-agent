# Read-only operational sheets

Native Tern routes these exact forms to the session-authorized `operations.report` RPC:

- `/mcp`, `/mcp list`: configured servers from Hermes config/plugin MCP authorities.
- `/mcp status`: cached connection state and tool counts, without connecting/probing.
- `/mcp tools`: cached registered tool names (including lazy registrations), filtered
  by the profile-owned/adopted MCP connection ledger. Names are not invocation authority.
- `/mcp catalog`: the existing Hermes MCP catalog's installation/enabled inventory.
- `/ssh`, `/ssh list`: the **current profile's single configured terminal SSH target**,
  using the same scoped terminal policy as the backend. This is not OpenSSH/OMP discovery.

The shared report sheet shows loading/ready/unavailable explicitly, the backend-owned
profile scope, exact report-only Copy and shared scrolling/Close actions. Approval
preemption and session/sheet identity fences preserve the main draft and discard late
results. No idle polling, timers, client-side operational store or list cap is added.

Other `/mcp` and `/ssh` forms show **unsupported management**, not a read-only success
report and not slash output. No command or mutation is sent. In particular add/remove,
reconnect, reload and auth are not exposed as native forms without canonical validation,
exact scope and readback. Existing Hermes CLI/dashboard management remains separate.

Only safe inventory fields cross this RPC: server names, closed state/auth labels,
cached tool names and counts; SSH host/user/port and identity-presence indicators.
URLs, command arguments, header/env values, OAuth tokens and SSH identity paths are
not returned. Failure exceptions are replaced by a generic unavailable state rather
than displayed as auth details. No SSH connection, MCP probe, OAuth flow, install,
reload or agent rebuild occurs as part of inspection.

Backend acceptance tests exercise real on-disk isolated profile configs and cached
connection ledgers. The native-control shortcuts journey reads the actual RPC for MCP
list/status/tools and SSH inventory and verifies unsupported SSH management sends no
operation and leaves config bytes unchanged.

Design reference: oh-my-pi MCP/SSH command controllers, Can Bölük / Stencil, MIT,
pinned `eb74cf84d8e16ac9b8c4fa5d7c43037023d016ac`. No OMP file layout/runtime is imported.
