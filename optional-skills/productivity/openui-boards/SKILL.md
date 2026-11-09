---
name: openui-boards
description: "Present facts as compact, read-only visual reports."
version: 1.0.0
author: Kevin Rajan (kvnloo), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [openui, charts, reporting, app-cards, generative-ui]
    category: productivity
    related_skills: []
---

# OpenUI Boards Skill

Emit a compact `openui-v2` program when the receiving Hermes client is known to render its panel catalog. This skill only formats supplied facts: it does not install a renderer, run tools, or make a card actionable.

## When to Use

- Use a board for file metrics, comparisons, time series, heatmaps, or factual results from an app connector when the client supports `openui-v2` **and** the chosen panel kinds.
- Use prose for explanations, brief answers, qualitative reasoning, unsupported panels, or clients whose rendering support is unknown. Prefer a short Markdown table if a board would not improve comprehension.
- Never send a board as the only answer. Add a normal Markdown summary **after** the complete fence for clients that show source instead of a rendered board.

## Prerequisites

- Known client support for `openui-v2` and the selected panels. Installing this optional skill alone does not enable rendering; do not assume the CLI, a messenger, or every Hermes Desktop version supports it.
- Verifiable input from the conversation or existing reads with `read_file`, `search_files` or configured connector tools. App cards require values actually returned by that app's tool in this turn; never invent prices, times, messages, checks, route geometry or map images.
- No added dependencies, scripts, credentials, or custom prompt-assembly changes.

## How to Run

Install once with `hermes skills install official/productivity/openui-boards`. When triggered, choose a supported panel for already-grounded data, emit one completed `openui-v2` fence, and follow it with a plain-language summary.

## Quick Reference

Use OpenUI's assignment syntax, **not** JSON, HTML, JSX, a Markdown table inside the fence, or function calls. Start with `root = Board("Title", "One-paragraph factual summary", [panelId, ...])` and then define every referenced panel as `panelId = PanelKind(positional, arguments)`. References inside Board's list are identifiers; every supplied data value is a literal (string, finite number, boolean, array, object). Argument names in the signatures below describe positional slots, not named-call syntax.

**Board signature:** `Board(title, summary, panels)`. Title at most 200 characters; summary at most 4,000; **1–8** panels in reading order. The whole `openui-v2` program is limited to **65,536 characters (64 KiB catalog limit)**. Panel titles at most 200 characters; nonempty labels at most 100; units at most 40. Numeric chart values are finite, non-negative, at most `1e12`.

| Panel | Positional argument order | Data contract |
|---|---|---|
| `Treemap` | `Treemap(title, sizeLabel, colorLabel, rows)` | 1–500 rows `{path, size, color}`. Nonempty `/`-separated paths at most 500 chars; no duplicates and no path that is both file and folder. |
| `BarChart` | `BarChart(title, unit, bars)` | 1–30 bars `{label, value}`; nonempty labels, non-negative values. Given order preserved. |
| `StackedArea` | `StackedArea(title, unit, categories, series)` | 2–60 category labels; 1–8 series `{name, values}` with exactly one value per category. |
| `Heatmap` | `Heatmap(title, unit, rows, columns, counts)` | 1–31 row labels, 1–48 column labels; exactly one count per row/column cell, including zeros. |
| `RideOptions` | `RideOptions(app, pickup, dropoff, options)` | `app` is `"uber"` or `"lyft"`; 1–8 unique-name options `{name, minutes, price, seats, arrival?}`. |
| `MailList` | `MailList(query, messages)` | 0–20 messages `{from, subject, snippet, time, unread, attachment?}`; `unread` is boolean. |
| `Route` | `Route(origin, destination, mode, minutes, distance, steps, via?, path?, map?)` | `mode` is `"drive"`, `"walk"`, `"transit"` or `"bike"`; 0–20 steps. Optional source-returned road, geometry, basemap. |
| `PullRequest` | `PullRequest(number, title, state, head, base, checks, conflicts, commits?)` | Positive integer PR number; 0–12 checks; integer conflicts 0–10,000; optional 0–12 commits. |

**App-card field limits and types:**

- Shared text fields at most 200 characters; required names nonempty. Ride `price` is 1–24 characters; `minutes` is a finite number from 0 to 100,000; `seats` is an integer from 1 to 20. Optional `arrival` is text. Duplicate ride option names are invalid.
- Mail `query` at most 200 characters. Each `snippet` at most 400; `subject`, `time` and optional `attachment` at most 200; `from` nonempty.
- Route `origin` and `destination` nonempty, `distance` and optional `via` at most 200 characters, step labels nonempty at most 200. `path` is 2–600 `[latitude, longitude]` pairs (latitude −90 to 90, longitude −180 to 180). `map` is `{image, bounds}`: only a tool-provided HTTP(S) image URL (at most 2,000 characters) and `[south, west, north, east]` bounds. Never invent geometry or a basemap, or supply an action URL.
- PR `state` is `"open"`, `"conflict"`, `"ready"`, `"merged"` or `"closed"`. Checks `{name, status, detail, started?, seconds?}` use `"pass"`, `"fail"`, `"running"` or `"skip"`; optional timing numbers range from 0 to 6,000,000 seconds. Commits `{title, sha, author, age, lane, branch?, conflict?}` require SHA length 4–12 and `lane` `"base"`, `"head"` or `"side"`; `conflict` optional boolean.
- PR consistency: `state: "conflict"` requires conflicts above zero; `ready`, `merged` and `closed` require zero conflicts; `ready` cannot have failing or running checks. Never imply check results without evidence.

## Procedure

1. Confirm the recipient can render `openui-v2` and the selected panel kinds. Otherwise answer in Markdown.
2. Collect facts with existing Hermes tools; retain precise units, order, values, and zero counts. Copy app connector results exactly or omit absent optional fields.
3. Choose the smallest useful 1–8 panels. Prefer a chart over hand-written HTML or long numeric tables when it makes the comparison clearer. Do not invent filler panels.
4. Write `root = Board(...)` followed by every referenced assignment in **one closed** `openui-v2` fence. Preserve positional argument order and omit absent trailing optional arguments. Never insert dynamic tool calls or executable expressions.
5. Append a Markdown summary with the main finding and caveats. It must be meaningful without the renderer.

## Worked Examples

Both completed programs below are copied verbatim from the T3 Code experiment's [source-demo-fences.md](https://github.com/kvnloo/t3code/blob/3cf6d0c655d22e249398fb7ea36198bf73b4e63d/experiments/openui-lab/source-demo-fences.md). Their numbers are **demo fixtures**, not live facts.

**Repository treemap with churn bars:**

```openui-v2
root = Board("Repository size and churn", "src/ui/chat.ts is the largest file; src/auth/login.ts has the most commits.", [map, churn])
map = Treemap("Size and churn", "LOC", "commits", [{path: "src/auth/login.ts", size: 80, color: 12}, {path: "src/auth/tokens.ts", size: 40, color: 6}, {path: "src/ui/chat.ts", size: 120, color: 4}, {path: "tests/auth.test.ts", size: 60, color: 7}])
churn = BarChart("Top 3 files by churn", "commits", [{label: "login.ts", value: 12}, {label: "auth.test.ts", value: 7}, {label: "tokens.ts", value: 6}])
```

Markdown fallback: `src/ui/chat.ts` is the largest file (120 LOC), while `src/auth/login.ts` has the most commits (12).

**Turns by model:**

```openui-v2
root = Board("Turns by model", "Wednesday had the most turns (16); Claude led on Tuesday.", [usage])
usage = StackedArea("Turns by model", "turns", ["Mon", "Tue", "Wed"], [{name: "Codex", values: [8, 4, 10]}, {name: "Claude", values: [4, 10, 6]}])
```

Markdown fallback: Wednesday has 16 turns; Claude leads Tuesday with 10.

## Pitfalls

- An unclosed or partial fence is source text, not a board. Unknown panels, missing references, empty panel lists, oversized values, and mismatched matrices are invalid.
- Boards are **read-only**. No `Query`, `Mutation`, generated state, tools, interactive side effects, booking, sending, merging, JavaScript, HTML, or arbitrary URLs. Local selections and drill-downs do not send chat messages.
- A client that renders charts may not yet support app cards. Respect the supported subset; the skill does not add UI widgets.
- Avoid unsupported latency claims. Smaller output can use fewer tokens than HTML, but speed requires a live comparison with the same model and facts.

## Verification

- Confirm signatures, numeric ranges, panel counts, lengths, and cross-field consistency against supplied data.
- Check the fence is closed and the Markdown fallback is useful alone.
- Repo checks: `scripts/run_tests.sh tests/skills/test_openui_boards_skill.py tests/skills/test_authoring_standards.py -q` and `python scripts/check`. Validate rendering in a compatible client; skill tests cannot prove UI support.
