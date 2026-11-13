---
name: tern-exploratory-devtools-evidence
description: "Use when exploring Tern dev-tool UX with pixel evidence."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [tern, qa, evidence, exploratory]
    related_skills: [hermes-agent, dogfood]
---

# Tern dev-tool exploratory evidence

## When to Use

Use for findings-only native Tern dev-tool testing, especially slash-command parity, language-server reports and isolated browser capability checks.

## Workflow

- Read the target checkout's `ui-tsp/e2e/README.md`, lane runner and developer help before driving it. Use a detached test worktree and exact-owned TERN_CONFIG_DIR, TERN_DAEMON_SOCKET, HERMES_HOME and numeric control endpoint. Never use an ambient user daemon or window.
- Verify the launched program's actual environment. A Tern login shell can remove inherited HERMES_HOME even when the daemon was launched with it. Prefer a short owned launcher that sets its environment explicitly, and inspect only allowlisted environment keys from the exact owned process. Do not print secret values.
- Wait for actual composer/overlay readback between text and Enter. Startup and gateway requests can outlive a successful control acknowledgement; blindly typing another launcher can submit it as a model prompt. Distinguish an idle shell from a ready frontend before `run`.
- Remember that Escape dismisses completion but can retain the slash draft. Explicitly remove that draft before the next command; doubled `//command` errors are operator artifacts, not command failures.
- Measure actual PTY cols/rows after resize instead of inferring them from pixels. Capture real PNG, visible tree and state together. Inspect the PNG; structure assertions do not qualify visual presentation.
- Compare completion promises against actual local dispatch. Classic aliases can conflict with frontend aliases, and display-only commands can claim stronger session-lifecycle semantics. Test the actual command in a disposable session and capture the resulting shell or retained context.
- Inspect terminal-formatted slash outputs as pixels. Rendering plain CLI/Rich output through Markdown can collapse rows and tables even when all expected text exists in the tree. Literal Markdown escaping can also turn backslash-parentheses into math.
- Label evidence boundaries explicitly: live language-server queries are not semantic fixtures; fixture replay is not a model turn; headless browser-interface unavailability is not successful frame/release testing; a signed-out native gate is blocked acceptance, never a reason to copy auth.
- Keep at most one owned serve session active. Close it before starting a baseline lane. Clean up only exact socket/home-owned processes, verify no survivors, validate every finding's evidence paths programmatically, and confirm tracked source stayed clean when testing is findings-only.
