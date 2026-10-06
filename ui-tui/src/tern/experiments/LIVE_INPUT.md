# Live native input + prose status

Variant A now combines the input prerequisite from #441 with the first live
transcript slice on #437.

## Preserved from #441

- The long-lived native event listener reads current Hermes busy/modal state on
  every event instead of startup values captured by its React effect.
- Unresolved completions disable native send in both the event gate and editor.
- The submitted native snapshot is invalidated synchronously before forwarding
  the exact text through Hermes' existing submission callback.
- Wrong-surface, wrong-editor and stale-text events do not submit.
- The backpressure regression from `8350d0cf` remains: A→B→A cancels B, and
  malformed/future ACKs never release frame credit.

## Added on A after that prerequisite

- settled user/assistant prose projects from Hermes' existing transcript rows;
- width-dependent virtual row keys are reduced to resize-stable semantic ids;
- the current assistant stream uses one stable native node;
- composer and transcript updates share the same bounded TSP frame-credit window;
- blocked intermediate transcript/composer states coalesce to the latest desired
  document before the next valid ACK.

This is still deliberately the smallest native slice. Intro/panel/trail/diff
families remain on Ink until each gets an explicit semantic contract.

## Still pending

- generic native tool lifecycle and failure history
- native subagent projection
- full approval/clarification/secret parity
- native cursor/Ink input handoff validation
- real Tern GUI capture at narrow/normal/wide widths
- attention measurements from the #436 glance-test protocol

The fixture/replay tools remain synthetic evidence. Passing unit/PTy tests does
not imply pixel, keyboard or attention validation in real Tern.

References: #432, #436, #437, #441.

Credit: Can Bölük / Stencil Labs for OMP/Tern native reference patterns; Hermes
contributors for the existing composer/transcript authority; Kevin Rajan for
the experiment direction. #441 is the provenance for the current-state input
handler now carried by Variant A.
