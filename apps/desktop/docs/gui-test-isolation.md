# Isolated GUI tests

Hermes tests must never launch a window on the developer's live desktop. Unit,
renderer, and browser tests stay headless. A test that genuinely needs an
Electron window runs inside the repository's nested compositor wrapper:

```sh
cd apps/desktop
npm run test:e2e
# one spec:
bash scripts/run-e2e-isolated.sh npx playwright test e2e/boot.spec.ts --reporter=list
```

`run-e2e-isolated.sh` starts Cage with the wlroots headless backend, one virtual
output, a private `XDG_RUNTIME_DIR`, and no hardware cursor. It removes the host
`DISPLAY`, `WAYLAND_DISPLAY`, Hyprland socket, and Sway socket before starting
the child. The wrapper fails closed with exit 78 if Cage is unavailable; it
never falls back to the live compositor. `e2e/fixtures.ts` independently refuses
a direct launch from a live Linux Wayland session.

Use Playwright `page`, locator, keyboard, and mouse APIs. They send protocol
input to the isolated browser context; do not use `wtype`, `ydotool`, `pyautogui`,
XTest, or other host-input injection in tests.

## Host fallback containment

The local Hyprland config has narrow rules for the fixture-owned class
`^HermesE2E-[0-9]+$`: route to `special:hermes-tests silent`, reject initial
focus, and reject later focus. This does not match normal Hermes, browsers,
terminals, or editors. It is only a final safety net; the nested compositor is
the execution boundary.

Current references checked against installed Hyprland 0.56.1:

- Hyprland window rules source: https://github.com/hyprwm/hyprland-wiki/blob/main/content/Configuring/Basics/Window-Rules.md
  (`workspace ... silent`, `no_initial_focus`, and `no_focus`).
- Hyprland variables source: https://github.com/hyprwm/hyprland-wiki/blob/main/content/Configuring/Basics/Variables.md
  (`misc:focus_on_activate`, `cursor:no_warps`, and workspace warp controls).
- Cage project: https://github.com/cage-kiosk/cage — a Wayland kiosk compositor
  built on wlroots; Hermes supplies `WLR_BACKENDS=headless` and
  `WLR_HEADLESS_OUTPUTS=1`.
- Playwright CI guidance: https://playwright.dev/docs/ci — Playwright is
  headless by default; headed Linux execution requires a virtual display.

## Rollback

1. Revert `apps/desktop/package.json`, `e2e/fixtures.ts`, and
   `scripts/run-e2e-isolated.sh`.
2. Remove the three `HermesE2E` rules from the Hyprland config and run
   `hyprctl reload`.
3. The optional user-local Cage bundle is
   `~/.local/opt/hermes-test-compositor`; remove that directory only if no other
   workflow uses it.
