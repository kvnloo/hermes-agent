---
name: phone-goal-vs-exec
description: Use when picking phone_goal or phone_exec for phone work.
---

# phone_goal vs phone_exec

Plugin `phone-goal`, source at `/mnt/zer0models/hermes-phone-goal`, symlinked into
`profiles/clean/plugins`. `phone_goal` runs a routine Android goal in ONE tool call:

1. Read the tree through the fast tree.
2. Build a vetted action table.
3. Jev picks a step (~0.16 s).
4. Run it and verify the screen changed.
5. Repeat.

`phone_exec` is a script you write, one model turn per script.

The full guide ships with the plugin: `skills/phone-goal/SKILL.md` in the repo.

## Rules

- **Use phone_goal for navigate-and-read goals.** Examples: "Settings > Battery level",
  "read the Android version". Measured on the S22+: 5-9 s for the whole goal (plus 2 agent
  turns). One model turn per step takes ~21-38 s.
- **Use phone_exec for the rest.** That means extraction or list walks, several apps, real
  typing, screens with no tree, or after phone_goal returns `uncertain`, `no_progress` or
  `max_steps`. Continue from the returned `final_screen` instead of rerunning.
- **Read the answer from `final_screen`.** `done` with `verified: false` is Jev's judgment,
  so check the value is in `final_screen`.
- **`needs_confirmation` means nothing was tapped.** Ask the person. Retry with
  `allow: ["<exact label>"]` only after a yes.
- **`jev_unavailable` is fail-closed.** Run `jev doctor` (skill jev-setup) or switch to
  phone_exec. Never guess the step yourself inside a phone_goal retry loop.
- **Device selection is per call.** Pass `serial` and `adb_server_socket`. The S22+ uses
  `adb-RFCTA1RZAQY-ZyDAxx._adb-tls-connect._tcp` and `tcp:127.0.0.1:5038` through
  `ssh -N -L 127.0.0.1:5038:127.0.0.1:5037 s22`. Do not use the S25 unless the owner is idle.
- **On the S22+, add `"restore": true`.** The tunnel's sshd and Tailscale live in the
  `dev.omalauncher` terminal app on the phone. Left in the background, it froze and the link
  dropped. Only the person can bring it back.
- **`fresh: true` only for apps without unsaved state (Settings).** It clears the app's back
  stack. Without it, a resumed sub-page confuses navigation.
- **Accuracy beats call count for Jev: use Bradley-Terry.** The owner prefers more fast
  Jev calls for a better choice, and names the method Bradley-Terry, not a bare knockout
  bracket (a bracket lets one bad match eliminate the right answer). After the safety
  denylist, collect pairwise Jev comparisons (round-robin for <= 6 candidates, a capped
  adaptive schedule between close-rated candidates above that), ask each pair in both
  orders to cancel position bias, count Jev confidence as a soft win, fit BT strengths
  (MM/Zermelo iteration with a small prior) and take the argmax; if the top-two margin is
  small, return `uncertain` with both instead of guessing. Run comparisons concurrently.
  Keep `flat` and `knockout` only as eval baselines; check the plugin's `chooser` option
  and its eval numbers for the current default.
- **Hand-written phone_exec scripts: read once, right after the action.** Most of a slow
  run is `wait_stable()` waiting out animations; a ~0.3 s sleep then one fast-tree
  `screen()` cut a demo from ~2.2 s to ~0.8 s per app switch. Jump to screens with
  `am start -n pkg/cls` and batch a whole sub-task per script (cost model in
  `home-k3s-fleet` `references/android-phone-workers.md`).
- **Benchmark from a terminal with the CLI.** Run
  `<phone-harness venv python> -m goalkit.cli ... --json` in the repo, plus
  `bench/bench.py` and `bench/summarize.py`.
