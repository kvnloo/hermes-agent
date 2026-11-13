---
name: anki-disposable-fsrs-bridge
description: Use when validating stock Anki imports and FSRS safely.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [anki, fsrs, safety, integration-testing]
    related_skills: [test-driven-development, grounded-citations, focus-safe-desktop-automation]
---

# Stock Anki qualification without personal writes

## When to Use

Use for stock Anki package building, import/review roundtrips, FSRS verification, and read-only game or learning bridges.

## Boundaries

- Inventory PATH, installed apps/packages, standard profiles, and plausible checkouts before installing. An incomplete disk scan does not prove that no historical collection exists.
- Keep official wheels, portable Python/Qt, caches, profiles, packages, backups, and evidence on the authorized private volume. Verify Anki/aqt wheel SHA-256 against official PyPI release metadata. Record CLI and PyPI versions separately; formatting can differ.
- Never launch a GUI on the host display as an agent. After a desktop-takeover correction, remain strictly terminal-only: no nested compositor, browser, screenshot, OCR, or focus input. Prefer installed `anki/buildinfo.py`, distribution metadata and CLI-entry source for version/argument discovery; importing `aqt` is unnecessary. If a version probe is separately allowed, remove every display/compositor/DBus route, use Qt offscreen and private HOME/config/cache, and label it version-only evidence.
- Require explicit approval for personal imports, configuration, optimization, rescheduling, and review writes. Writable tests belong only in newly created path-restricted disposable collections with a matching marker.

## User-invoked launcher and approval gates

- Read the installed CLI consumer before composing arguments. Stock Anki 26.9.3 `--profile` selects an existing registered name; it does not create one. Use an explicitly approved empty-base bootstrap and human rename rather than assuming a requested name was created.
- Bind `ANKI_SINGLE_INSTANCE_KEY` to the dedicated base. Stock Anki otherwise uses a user-global key independent of `--base`, so even a different base can raise/reuse an unrelated running GUI.
- Default to read-only proposals. Separate approval for fresh empty-directory preparation, first user-run GUI opening, later exact existing-profile selection, and private review export. Never supply human approval or infer study attestations from revlog. A GUI open can write normal collection/profile state even when the wrapper does not import or change settings.
- Enforce the exact private mount identity, literal paths, owner-only managed state, no symlinks/hardlinks, and no tracked private data. When the authorized private root is inside an outer repository's ignored data tree, verify both actual Git ignore coverage and an empty tracked-file set; a blanket ancestor `.git` ban would reject the legitimate volume. Reject nested repositories.
- Exercise launcher arguments and environment filtering with harmless terminal subprocesses on isolated fixtures. Label these stub tests, not GUI verification. Real review-export proof uses only new marked disposable backend collections, a read-only SQLite transaction including committed WAL rows, deterministic evidence IDs, collision refusal, private-text canaries, and source schedule/history/config preservation checks.

## Real backend proof

- Import `anki.collection.Collection` before model helpers; importing models first can encounter circular imports.
- Pin the backend and inspect installed signatures. In 26.9.3 use `col.decks.get_deck_configs_for_update(deck_id).fsrs`, not a guessed `Collection.fsrs_enabled` property.
- Export with explicit scheduling/deck-config/media/legacy flags. Stable concept IDs plus deterministic GUIDs provide logical identity; stock numeric IDs are preserved by re-import within a destination, not guaranteed across independent empty collections.
- Test import, separately rebuilt-package re-import, note/card identity, unchanged revlog/schedule/deck configuration, real rendering, and backup restoration.
- Enable FSRS only in the disposable fixture. Fetch `sched.get_queued_cards()`, pass its states to `sched.build_answer`, call `sched.answer_card`, and verify actual revlog rows plus card.memory_state. Exercise all four ratings without inventing due cards or intervals.
- Label automated answers synthetic. Human review count stays zero until genuine human study occurs.

## Read-only bridge

- Never open the personal source with Anki: opening can migrate or change it. Use SQLite `mode=ro`, query-only, and online backup into a private temporary DB; ask stock Anki for the queue on that copy. Do not copy just the main DB while WAL writes are active.
- Use `contextlib.closing` for SQLite connections. Their context manager controls transactions but does not close connections. Run Python 3.13 tests with `-W error`; also close HTTPError response objects in tests to avoid leaked sockets.
- Describe queues as Anki next-available cards, including new/learning-ahead cards. Raw due values have state-dependent units; never derive a second schedule from them.
- Serve only allowlisted canonical public practice fields, not edited personal answers or held-out files. Verify with a private-answer canary.
- Bind loopback only, enforce exact Host/Origin allowlists, reject HTTP writes, bind port 0 directly, and fail on explicit port collisions. Exercise actual HTTP and stop owned servers cleanly.

## Events and evidence

- Atomically spool one event per actual disposable revlog row, marked test/synthetic using the consumer's allowed fields. Verify the actual consumer excludes these from human ingestion without opening its production projection.
- Derive event identity from fixture identity plus revlog identity. Replay emits existing evidence idempotently and never answers cards again; conflicting payloads fail closed.
- Keep fetched public-source snapshots privately, with exact excerpt/hash replay. Bind concept URLs to the retrieval manifest; a trusted hostname alone does not prove a link exists. Separate mechanical atomicity checks from semantic editorial review.
- Capture only stdout when writing dependency lockfiles from package-manager output; terminal results may merge stderr banners into otherwise valid requirements. Exercise the actual package-manager consumer and install the lock into a fresh private environment before calling it reproducible.
- Receipt versions, commands, card/package counts, source replay, actual import/review/HTTP results, unchanged-source evidence, and blockers. GUI usability and human learning quality are separate acceptance criteria.
