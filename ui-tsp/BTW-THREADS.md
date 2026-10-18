# BTW side threads

`/btw` opens gateway-owned side history; `/btw <question>` starts a new side
thread. Select any previous thread to continue it, or choose **New side question**.
Side questions, streamed answers and errors never become main transcript messages.

- Tab cycles history / reader / composer. Ctrl+N/P selects threads.
- Arrow, Page Up/Down and Home/End scroll only the selected sheet pane.
- Enter in the composer or Alt+Enter sends. Ctrl+X stops only the selected side turn.
- Copy sends the selected thread's question/answer text through OSC 52.
- Escape / Return to main draft restores the main composer and caret.
- Per-thread unsent drafts survive selection, sheet close and approval preemption.
  They are presentation state, not persisted history, and are cleared on session adoption.

Hermes owns `btw.list`, `btw.submit`, `btw.cancel` and `btw.update`. History is
stored under conversation-owned keys in the existing profile `state.db` metadata,
not in a renderer store or a second database. Atomic DB transactions admit at most
one running turn per thread. Thread revisions prevent late RPC snapshots from
replacing newer stream events. Cancellation is exact session/transport/thread/turn
scoped and returns canonical readback; late streams cannot revive a cancelled turn.
A lost worker is explicitly cancelled on the next history read, allowing follow-up.
No idle polling, timers, UI history cap or main prompt-cache mutations are added.

The existing cache-parity fork denies tools and streams real text deltas. The
existing one-shot fallback returns a final answer (no fabricated streaming); an
in-flight fallback provider call may finish after cancellation, but its output is
not adopted. Side work is not restarted automatically after a gateway restart.

Design reference: oh-my-pi BTW history panel by Can Bölük / Stencil (MIT), pinned
`eb74cf84d8e16ac9b8c4fa5d7c43037023d016ac`. No OMP runtime/store code is imported.
