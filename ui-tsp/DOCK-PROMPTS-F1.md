# Dock prompt regression checks

The F1 lane uses the real App, native layout, accessibility tree and keyboard
dispatch in an isolated `tern serve`. Gateway replies and recorder events are
presentation fixtures. It does not run a model, execute the displayed command,
or open a microphone.

```sh
# Set a private scratch directory per command. The runner places its config,
# socket and child HOME there, and stops only its owned processes.
env TMPDIR=/absolute/private/scratch python ui-tsp/e2e/dock_prompts_geometry.py \
  "$PWD" --baseline --receipts /absolute/private/receipts/before
env TMPDIR=/absolute/private/scratch python ui-tsp/e2e/dock_prompts_geometry.py \
  "$PWD" --receipts /absolute/private/receipts/after
```

The baseline loader uses the affected modules verbatim from `724b2aaec5`.
An `expected-red` baseline result retains each failing assertion. The after
run must pass. Each run saves measured 80x28, 100x30 and 160x44 pane sizes,
PNGs, native trees, layout dumps, accessibility trees and cleanup receipts.
AX selected-option containment permits the native one-pixel selection border.

| Finding | Cause and change | Regression |
| --- | --- | --- |
| G06-001, G09-03 | Unbounded approval choices pushed the command and warning above the viewport. Bound the native choices scrollport to four lines and wrap the command. Keep command and warning outside the choice scrollport. | Rendered command/warning containment before and after keyboard selection at all three sizes; selected-option containment. |
| G01-002 | A long clarify list expanded the dock above the viewport. Bound the native list to six lines. | Rendered question containment before and after selecting the last option at all three sizes. |
| G01-004 | The composer treated all dock prompts as approvals. Pass the prompt kind and show an answer-question hint for clarify. | Native rendered text plus the visible/hidden hint test in `finish-clarify-docking-notes.test.ts`. |
| G01-001 | Clarify consumed Escape before capture cancellation. Route the registered interrupt action ahead of prompt, Vim and completion ownership while capture is active. | Real App dispatch with Vim enabled, cancel RPC, no clarify answer on first Escape, ignored late final text, retained draft/caret and second-Escape skip. The serve fixture also checks cancellation dispatch. |
| G09-06 | The choice list had no accessible name. Name it with the exact question. | Native ListBox name at all three sizes plus the rendered-view test. |
| G01-005 | Not reproduced on `724b2aaec5` with this host's Tern. That base already uses measured whole-segment status priorities. No additional product change. | Both INSERT and NORMAL remain single-line at all three measured sizes in baseline and after captures. |

This lane covers the reported long-path approval and twelve-choice question.
It does not certify arbitrary-size command bodies, arbitrary-size question text,
very short windows, OS screen readers, real audio hardware, or signed-in native
windows. PNGs must be visually reviewed separately from semantic assertions.
