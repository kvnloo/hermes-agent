---
name: oss-checkout-install
description: "Use when installing or updating OSS apps, tools or ML venvs."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [oss, install, clone, node]
    related_skills: [github, upstream-contribution]
---

# OSS checkout install

## When to Use

Use when the user asks to clone a project into their oss folder and install it.

## Procedure

1. "My oss folder" means `/home/kvn/zer0/oss` unless they name another path. Do not use the large workspace OSS collection for that phrase.
2. Compare the upstream and fork default-branch SHAs. Clone the tree those SHAs identify. If they match, clone upstream and add the fork remote. Do not choose by `pushedAt`.
3. Read the selected revision's repo engines, runtime-version files and `packageManager` before installing dependencies. Re-read them after changing the source revision: a newer branch can require a different Node and package manager than the checkout first inspected. Use the declared Node even when the shell's Node is newer; the package manager will not switch it for you.
4. Run the documented user-space install with the repository's declared package manager, then the named CLI build. Put a small wrapper on `~/.local/bin` that pins that Node and execs the built entry. Verify with a login shell (`bash -lc 'command -v <cmd> && <cmd> version'`), not only a PATH you exported in the same command.
5. A desktop or native build that needs a system library is a separate install. If `sudo` requires a password, do not hang on it and do not claim the app is installed. Report the CLI as installed and name the missing package. A stale desktop handler pointing at an old debug binary is not an install. When they ask for the dependency command, reply with that command only.
6. A script that runs `cargo tauri` does not get that subcommand from `npm install`. Install a published 2.x `tauri-cli` (`cargo info tauri-cli`, then `cargo install tauri-cli --version 2.9.1 --locked`). Do not pass the app crate's `tauri` version as the CLI version; crates.io often has no such release. Build with `npm run tauri:build -- --no-bundle` so the bundler does not demand signing keys. The GUI binary may share the CLI's name; install it as a separate launcher (`o8-desktop`) and a desktop entry. Do not replace the CLI wrapper.
7. When the user says the dependency command is done, continue the desktop build in that checkout. Do not wait for them to repeat "install it".
8. Install proof is `ldd` with no missing libraries, plus a desktop entry whose `Exec` is the new release binary. When the user authorizes GUI testing, exercise that exact binary on an isolated display/profile without stealing focus or attaching to the live instance. Otherwise hand over the verified launcher for the user to open. A Wayland protocol error in an agent shell is not proof of a failed link, and a successful link is not proof of a working window.

On Arch-family hosts the Tauri 2 desktop floor is:

```sh
sudo pacman -S --needed webkit2gtk-4.1 base-devel curl wget file openssl appmenu-gtk-module libappindicator-gtk3 librsvg
```

## Update an existing OSS app to latest and launch it

1. Find the canonical checkout before cloning anything. Product checkouts live under `/workspace/zer0/products/<app>`, with sibling worktrees named `<app>-<topic>`. Owner notes may sit in a related product's `docs/<app>/` (for example flowkit `docs/noop/WORKFLOW.md`). Copies under `/mnt/zer0models/zer0-tier/` are not Git checkouts. Run `git worktree list` and `git remote -v` first.
2. Run `git fetch --all`, then report how far behind each remote is with `git rev-list --count HEAD..upstream/main` and the newest tag. Fast-forward `main` without checking it out: `git fetch . upstream/main:main`. That updates the ref only when it is a fast-forward. Leave the feature worktrees alone; rebasing them is the owner's call.
3. Before building or porting, read upstream's supported-platform list (the README platform table and the top-level tree). The user's host may have no official build. Say so plainly, and rank the options by effort. When a large drift makes a local port branch stale, name the drift as the cost.
4. Prefer the official release artifact over a source build or port: `gh release view <tag> -R <owner>/<repo> --json assets`. For an Android-only app, install the APK on the user's phone with `adb install -r` once `adb devices -l` lists it. If no device is listed, ask the user to plug in with USB debugging on. Pairing with hardware needs taps on the phone, so plan to drive the UI with the maestro-local-android skill and hand the taps to the user.
5. Apps that pair with wearables over Bluetooth need real BLE. Confirm Bluetooth passthrough before choosing an emulator, Waydroid or a VM, because without it the UI runs and still never sees the device.
6. Before promising that a device will work, read the release notes for the user's exact hardware model (`gh release view <tag> --json body --jq .body | grep -i -A4 '<model>'`). Lead with any limit they state, such as live data only with no history.

### Android sideload (adb)
1. Download the release APK into the canonical store, `/mnt/zer0models/project-artifacts/<app>/releases/<tag>/`, and record its `sha256sum`.
2. Before installing, list the existing builds: `adb shell cmd package list packages --show-versioncode --user 0 | grep <app>`. Older debug or staging builds use a different application id and stay installed side by side. Force-stop them so they do not hold the Bluetooth device, and leave uninstalling or migrating their data to the user.
3. Run `adb install -r <apk>`, then repeat the list to get the real package id. Release APKs often carry a flavor suffix such as `.staging`. `dumpsys package <guessed id>` prints nothing for a wrong id, which can look like a failed install.
4. Grant runtime permissions with `adb shell pm grant <pkg> android.permission.{BLUETOOTH_SCAN,BLUETOOTH_CONNECT,POST_NOTIFICATIONS,ACCESS_FINE_LOCATION}`. Launch with `adb shell monkey -p <pkg> -c android.intent.category.LAUNCHER 1`. Take a screenshot with `adb exec-out screencap -p > <store>/<step>.png` and look at it before each tap.
5. First-run screens that ask the user to attest to legal or terms statements (ownership, affiliation, liability, ToS risk) are the user's to tick. Stop there, summarize the statements, and continue only after the user says they are past that screen.
6. Mention a low battery before a long Bluetooth pairing session.

## Switch an installed app to a nightly or beta channel

1. Find how it is installed first: `command -v <app>`, `pacman -Qs <app>`, `/opt/<app>*`, and the launcher script. An AUR `-bin` package in `/opt` is a repackaged upstream AppImage that pacman owns, so the app cannot update itself.
2. Look for the official channel before building anything:
   - `gh release list -R <owner>/<repo> -L 8` shows the nightly or beta pre-releases.
   - In an extracted AppImage, `resources/app-update.yml` (`channel:`, `releaseType:`) shows the channel the build updates from. An `updateChannel` string in `app.asar` means the app has an in-app channel setting.
3. Present the least-effort official path first: a self-updating pre-release AppImage, which needs no sudo. Offer the AUR `-nightly-bin` package second, for users who want pacman to own it. Do not lead with makepkg. The user asks why something was "built" when a release channel exists.
   - Put the AppImage in `/mnt/zer0models/apps/<app>/<App>.AppImage`, a canonical, writable folder that the updater can replace in place. Do not leave it as a loose file in `~`.
   - Add a launcher at `~/.local/bin/<app>` that execs the AppImage. Copy any env setup the old wrapper did, such as `CODEX_CLI_PATH`.
   - Add a desktop entry at `~/.local/share/applications/<same-id>.desktop`. Using the same file id as the system entry overrides it without sudo. Copy the icon under a new name into `~/.local/share/icons/hicolor/512x512/apps/`.
   - Run `xdg-mime default <id>.desktop x-scheme-handler/<app>` so the app's links still open it.
   - Verify with `bash -lc 'command -v <app>'`.
   - If the app is already running, do not kill it to smoke-test. Tell the user to quit it, remove the pacman package, and open the new entry.
   - Delete the `aur-builds/<pkg>` directory once the AppImage is copied out.
4. If you do use the AUR package: read the PKGBUILD, `makepkg -f` in `/mnt/zer0models/cache/aur-builds/<pkg>`, and confirm the AppImage sha256 matches GitHub's asset `digest`. Say that "build" only repackaged the official artifact.
5. Before the switch, check:
   - `pacman -Qi <old> | grep -E 'Provides|Conflicts'`, because pacman will offer to remove the stable package.
   - The new binary name from `tar -tf <pkg>.pkg.tar.zst | grep usr/bin`.
   - The Electron `name` in `app.asar` `package.json`. It gives the `~/.config/<name>` data dir. When stable and nightly share that dir, back it up to `/mnt/zer0models/hermes-backups/<app>/` first, because a nightly can migrate data that stable cannot read.
6. sudo needs a password here. Hand over one command (`sudo pacman -U <pkg>`) and say which prompt to accept. Verify the version after the user confirms.
7. Before each follow-up step, re-check the state with `pacman -Q | grep <app>`. The user may have run the handed-off command already, even after switching plans. Then the cleanup is `sudo pacman -R <the package they actually installed>`, not the one you planned to replace.

## Install a separate experimental desktop build

1. Verify the requested fork and pin its actual source SHA before choosing integration points. Compare it with the local checkout; a missing feature in an old checkout is not evidence that the current fork lacks it. After fetching the intended base, repeat relevant source searches before designing a parallel implementation.
2. Inspect the existing executable, desktop entry and startup paths without modifying them. Give the experimental build its own executable/launcher and desktop-entry id; unlike a channel replacement, do not override the installed entry or default protocol/MIME handler.
3. Trace runtime storage and startup identity before packaging. Isolate application id/name, Electron userData/session and single-instance locking, backend home/database, ports, protocol registration and updater destination. Renaming the package alone does not isolate its runtime state.
4. Keep the live database read-only. If realistic test data is necessary, use the project's consistent snapshot procedure into the sandbox, never a symlink or a live read-write connection.
5. Verify the installed launcher resolves to the experimental binary and that the running build uses its isolated paths. Report source preparation, successful build, installation and real-window qualification separately; none proves the next stage.
6. When packaging infrastructure is unavailable, block only the dependent build/install steps. Continue source edits, regression tests and permitted lightweight smoke checks that do not depend on it; a packaging failure is not a reason to abandon implementation. Respect explicit worker holds rather than bypassing admission, and retain a precise remaining acceptance checklist.
7. For an autonomous dogfood request, do not ask the owner to repeat authorization or choose routine implementation details. Work through unblocked steps and report useful verified results or a genuinely task-wide blocker, not repeated infrastructure status. Do not describe a smoke-tested renderer as an installed dogfood app.

## Before saying something is not installed

The owner has many ML runtimes already installed in their own venvs (ComfyUI with models and custom nodes, Hunyuan3D, TRELLIS.2, Unsloth, vLLM, Ollama/llama.cpp SLMs, faster-whisper). "Not running" (no port answering, no service) is not "not installed". Probe these before proposing an install or a cloud fallback: `/mnt/zer0models/<app>/` (look for `.venv`), `/mnt/zer0models/venvs/`, `/mnt/zer0models/local-3d/`, `/mnt/zer0models/zer0-models/{gguf,huggingface}`, `ollama list`, and `systemctl --user list-unit-files | grep -iE 'llama|ollama|comfy'`. Keep `find` bounded with `-maxdepth 3` and `timeout`, because the 4 TB drive is huge. Smoke the venv (`env -u PYTHONPATH -u PYTHONHOME <venv>/bin/python -c 'import torch; print(torch.cuda.is_available())'`) and write a short inventory file for any subagents. Launch an existing install as an owned process on a free port; never modify its tree.

## GGUF reasoning model installs

For local reasoning-model downloads and GPU smoke comparisons, follow [GGUF qualification](references/gguf-reasoning-qualification.md). Reuse the installed CUDA runtime, pin artifact provenance and distinguish response-budget exhaustion from an incorrect answer.

## Python / ML packages (pip-installable, no clone)

For `pip install <pkg>` asks (unsloth, vllm, etc.) follow `references/python-ml-venv.md`: dedicated uv venv under `/mnt/zer0models/venvs/<pkg>`, a Python the package supports, then an import + GPU smoke test before reporting.

## Vendored skill packs (pstack etc.)

To update a skill pack copied from an upstream repo into a profile's `skills/<pack>/`, follow `references/vendored-skill-packs.md`. It covers the diff, keeping local edits, re-applying them, verifying, and the `SOURCE.txt` provenance file.

## Pitfalls

- A doctor check that cannot reach a local server means the control plane is down, not that the CLI build failed. Say which of those you verified.
- Do not `npm install` on a Node outside the repo's engines range. The install can succeed and the app still refuse to run.
- Do not assume `npx tauri` exists because `@tauri-apps` is in `node_modules`. The build script shells out to `cargo tauri`.
