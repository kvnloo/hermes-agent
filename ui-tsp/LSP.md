# Native LSP inspection

Use `/lsp symbols <path>`, `/lsp references <path> <line> <column>` or
`/lsp hover <path> <line> <column>`. Paths (including spaces) are relative to
the session workspace, or absolute within it. Positions are **one-based UTF-16
code units**, not bytes or Unicode code points. The generated `lsp.query`
contract owns the result variants.

The gateway queries the existing profile-local Hermes LSP service, using its
workspace detection, trust, exclusions, disabled-server and broken-server gates.
It opens/synchronizes the actual file and sends only the three read-only LSP
methods. No rename, workspace edit or execute-command endpoint is exposed. A
remote session never probes a same-named gateway-host file. Unsupported methods,
missing servers and timeouts are unavailable, malformed responses/server errors
are errors, and only successful null/empty responses mean checked-empty.

The native sheet does not create a model turn or synthetic transcript/tool rows.
It issues one explicit request, preserves the composer and dismisses without
reopening when a late response arrives. No frontend polling or idle timer is
introduced. `/help` and slash completion expose the command; no new key chord is
registered. References are grouped by actual returned file. Symbols retain stable
producer IDs, nesting and full range/selection metadata; wrapping location rows
keep long tree labels available at narrow widths. Hover honors Markdown, literal
plaintext and language-marked source rather than guessing from result prose.

`view/tools.tsx` also accepts the same `lsp_result` envelope on an `lsp` result
for stored results from a plugin/native producer. **This does not register a new
model tool.** Old/foreign/malformed results keep the generic literal fallback.
File links are enabled only when the gateway is not attached and the session
explicitly reports the local backend. Tern owns opening the file; its column
fragment support remains host-dependent.

Validation: Python tests run a real framed mock-server subprocess through the
existing service, and cover RPC transport/workspace fences. The App/SDK tests
exercise live completion and stored-message replay, full result retention,
empty/error distinctions, native Close, late completion and composer preservation.
The `lsp-diagnostics` E2E journey additionally replays explicitly labelled semantic
fixtures at measured widths; fixture replay is not a real language-server query
or a signed-in native-window receipt. OMP's grouped-reference/tree design at
`packages/tui/src/tools/lsp.ts` (Can Bölük / Stencil, MIT) informed presentation;
semantic data is structured Hermes output, not parsed OMP text.
