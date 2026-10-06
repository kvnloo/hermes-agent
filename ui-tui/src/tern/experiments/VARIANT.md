# Variant B — Hermes design-language baseline

Issue: #436

## Question

How much of Hermes' design language survives when we keep **Hermes hierarchy and
interaction rules** but let Tern own the outer application chrome?

## Canonical evidence

Read first:

- `apps/desktop/DESIGN.md`
- `apps/desktop/pr-assets/session-source-folders.png`
- `apps/desktop/pr-assets/profile-launch-menu.png`
- current Hermes TUI interaction flows

This variant is not "Desktop squeezed into a terminal." The transferable pieces
are flatness, spacing, semantic hierarchy, approvals, progressive disclosure,
intent-before-automation and Nous identity.

## First implementation slice

Use the same semantic regions and fixture as Variant A, but adapt:

1. transcript hierarchy
2. composer/status grouping
3. approval/clarification salience
4. tool completion/failure treatment
5. Hermes queue/subagent disclosure language

Do not add persistent navigation just because Desktop has it; Tern already owns
window/tab/pane navigation.

## Success condition

A five-second glance should read as Hermes without needing a duplicated Desktop
sidebar or titlebar.
