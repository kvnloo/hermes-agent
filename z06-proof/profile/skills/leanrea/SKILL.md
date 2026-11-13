---
name: leanrea
description: Reverse engineer shipped software with plain local CLI tools, no MCP needed. Covers Electron/JS bundles, native Mach-O/ELF/PE, Go/Rust/.NET/Flutter/WASM binaries, APKs, SQLite, pcaps, firmware and websites. Use to explain how a feature works, extract versions/deps, compare builds, or rebuild a feature.
---

# leanrea: fast path

You already know these tools. This file only lists the fastest command for each target, and the traps.

## Rules
- Work on a copy (`cp -c` on APFS is instant). Put each extraction in a new dir under `$TMPDIR/re/<name>`. Reuse an extraction if one exists.
- Route by `file -b T` and the magic bytes first. Run the cheapest inventory next. Only then decompile or read code.
- `rg` skips hidden and ignored files, and bundlers hide code (Electron: `.webpack/`, `.vite/`). Always search extracted trees with `rg -uu`.
- Never `cat` a big or minified file. Slice it: `rg -o '.{0,200}NEEDLE.{0,200}' F | head`. Dump a disassembly once to a file, then grep that file.
- Batch independent probes into ONE shell call with `;` and `echo '--- name'` markers (quoted: zsh expands a bare `==x`). Cap every output with `head` or `-m`.
- Answer from evidence. In the answer, mark each claim as **seen** (cite file:offset, or a symbol/string) or **inferred**. A fact you did not find is **unknown**, not "absent". Static reading is not observed execution.
- A missing tool is not a blocker. Use the fallback in the same row, or `brew install <x>` if the user allows it.
- Turns cost more than bytes. Aim for 2–4 tool calls: one batched recon call, one or two targeted slices, then answer. Stop when every item you were asked has evidence. Do not re-verify what you already saw.

## First move: one call each, paste and run
Native (Mach-O):
```sh
T=./bin; D=$TMPDIR/re/$(basename $T); mkdir -p $D; file $T; lipo -info $T; otool -L $T; echo '--- EXPORTS'; nm -gU $T | head -150; echo '--- IMPORTS'; nm -u $T | rg -v '^__Z|napi_' | tr '\n' ' '; echo; echo '--- STRINGS'; strings -a -n 6 $T | rg -v '^[_$.]' | head -400; otool -tV $T > $D/dis.txt; echo '--- FUNCS'; rg '^[_a-zA-Z].*:$' $D/dis.txt | rg -v '^_?_?Z?N?St3' | head -150
```
Then read one function: `awk '/^FUNC_LABEL:$/{p=1;next} p&&/^[_a-zA-Z].*:$/{exit} p' $D/dis.txt | rg 'bl|b\.|cmp|literal|mov\s+w2'`.

Electron:
```sh
A=./app.asar; X=$TMPDIR/re/asar; rm -rf $X; npx -y @electron/asar extract $A $X && jq '{name,version,main}' $X/package.json; find $X -path '*/node_modules' -prune -o -type f \( -name '*.js' -o -name '*.node' \) -print | head -60; ls ${A}.unpacked/node_modules 2>/dev/null; rg -uu -l --glob '!node_modules' 'exposeInMainWorld' $X
```
Then slice the needle across the bundle: `rg -uu -o --glob '!node_modules' '.{0,250}NEEDLE.{0,250}' $X | head -20`.

Go: `go version -m T` alone usually answers the question.

## Router
| Target (detect) | Fastest path |
|---|---|
| Electron app (`*.app/Contents/Resources/app.asar`) | `npx -y @electron/asar extract app.asar X` (also see `app.asar.unpacked/` for `.node` addons). Entry point: `jq .main X/package.json`. Surface: `rg -n -o '.{0,120}(ipcMain\.(handle|handleOnce|on|once)|ipcRenderer\.(invoke|send|sendSync|on)|contextBridge\.exposeIn(Main|Isolated)World|webPreferences|preload:|nodeIntegration|contextIsolation|sandbox|\.node\b).{0,160}' -uu X --glob '!node_modules'`. App-specific IPC wrappers often hide the channels, so also run `rg -uu -o '"[a-z]+:[a-z0-9:-]+"' X/<main> \| sort -u`. Fuses: `npx -y @electron/fuses read --app A.app`. |
| Web bundle / minified JS | Find `sourceMappingURL`. If the map has `sourcesContent`, dump the sources: `jq -r '.sources[]'`. For webpack, grep the module ids, then slice around the hit. For pretty-print: `npx -y prettier --parser babel F > F.pretty.js`, then read with line ranges. |
| Hermes / bytenode / V8 snapshot | Hermes magic is `c6 1f bc 03` (`index.android.bundle`): use `hermes-dec` / `hbc-decompiler`. `.jsc` (bytenode) cannot be decompiled: use strings and runtime hooks. |
| Mach-O (`file`: Mach-O) | `lipo -info` (thin first: `lipo -thin arm64 -o T1 T`). Then: `otool -L` (libs); `xcrun dyld_info -exports -imports`; `nm -gU` (exports) / `nm -u` (imports = the capability map); `strings -a -n 6`; `otool -l \| rg -A3 'LC_(RPATH\|BUILD_VERSION)'`; `codesign -d --entitlements :- T`; `otool -ov` (ObjC classes/methods); `xcrun swift-demangle --compact`. |
| Native code logic | `otool -tV T > $D/dis.txt` (or `llvm-objdump -d --no-show-raw-insn -C`). Find the function: `rg -n '^_?.*Name.*:$'`. Read the call/string trail: `awk '/^FUNC:/{p=1} p&&/^[_a-zA-Z].*:$/&&!/FUNC/{exit} p' dis.txt \| rg 'bl\|call\|literal\|cmp'`. otool labels string literals and stubs inline, which is often enough. Only for real pseudocode: Ghidra `analyzeHeadless $D p -import T -postScript DecompileAll.java -deleteProject` or `r2 -qc 'aaa; pdc @ sym.X' T`. |
| ELF / PE | `readelf -hlSW`, `readelf -dW` (NEEDED), `nm -D --defined-only`, `objdump -d -M intel`. PE: `objdump -x`, `pefile`/`wrestool` for resources. checksec: `pwn checksec`. |
| Go (`__go_buildinfo`, `.go.buildinfo`) | `go version -m T` gives the toolchain, path, mod, deps and build flags in one call. Without Go: `strings -a T \| rg -m1 -A200 'Go buildinf' `. Symbols survive stripping: `go tool nm T \| rg main\.`. |
| Rust | Deps (cargo-auditable): `cargo audit bin T`, or extract `.dep-v0` / `__DATA,.dep-v0` and zlib-inflate it. Compiler: `strings -a T \| rg -o '/rustc/[0-9a-f]{40}' \| sort -u`. Crates from paths: `strings -a T \| rg -o '[a-z0-9_-]+-[0-9]+\.[0-9]+\.[0-9]+/src' \| sort -u`. |
| .NET (`file`: Mono/.Net) | `ilspycmd -p -o X T.dll` (install: `dotnet tool install -g ilspycmd`), then `rg`. P/Invoke: `rg DllImport X`. NativeAOT/IL2CPP are native: use the native rows. |
| Android APK | `jadx -d X --show-bad-code a.apk` then `rg`. Resources/manifest only: `apktool d --no-src -o X a.apk`. Quick look: `unzip -l a.apk`. `lib/*/libflutter.so` means Flutter (Dart AOT: `blutter`); `libhermes.so` means React Native (Hermes row). |
| Flutter snapshot hash | In `libapp.so`, find magic `f5 f5 dc dc`; the 32 hex chars at +20 are the snapshot hash. Map it to a Dart version. |
| WASM | `wasm-objdump -x`, `wasm2wat`, `wasm-decompile` (WABT). |
| SQLite | Copy the db, plus the `-wal` file if present. `sqlite3 'file:C?mode=ro' '.schema'`, then `SELECT * FROM t LIMIT 20`. |
| plist / nib / car | `plutil -p F`. Info.plist holds the bundle id, URL schemes and privacy strings. Asset catalogs: `assetutil --info Assets.car`. |
| pcap / HAR | `tshark -r C -q -z conv,tcp`; `tshark -r C -T fields -e dns.qry.name -e tls.handshake.extensions_server_name -e http.request.full_uri \| sort -u`. HAR: `jq -r '.log.entries[].request \| .method+" "+.url'`. |
| Firmware | `binwalk -e F` or `unblob -e X F`. Then route each extracted binary through this table. |
| Website | `curl -sL URL` for the HTML and script srcs, then fetch the JS and slice it. For runtime behavior, use a headless browser with a network log (Playwright `page.on('request')`) or Chrome `--remote-debugging-port`. |
| Running app / runtime | macOS: `lldb -p PID`, `dtrace`/`fs_usage`/`log stream --predicate 'process=="X"'`. Electron main: `--inspect` (only if the RunAsNode/inspect fuses allow it). Android: `adb logcat`, `frida -U -f pkg -l hook.js`. |

## Speed patterns
- Strings and imports first. On a small binary, `nm -u` + `strings` + the export list usually answer "what does it do" with no disassembly.
- To find who uses a string: get its address from `otool -tV` "literal pool for" comments, or `rg -n 'literal pool for: "X'`. Then find the enclosing function label above that line.
- A C++ name in a `bl` target already tells you the protocol (for example `getpeereid`, `write`, `std::hash`). Read the call sequence, not every instruction.
- For JS, go from the native/JS boundary inward: find the native call, then its caller class, then the IPC registration, then the renderer/preload.
- Comparing versions: diff the inventories (`nm`, the module list, `go version -m`) before you diff any code.
- Rebuilding: write the minimal reimplementation, then test it against the original (same inputs, same outputs).

## Firmware-specific shortcuts and stop gates

- Search the observed BSP/platform ID as well as the retail chip name before declaring upstream support missing: BCM6755 firmware uses a 47622 platform identity, and upstream `bcm47622.dtsi` is a closer lead than searching only `6755`. Distinguish minimal reference-board support from an exact-device OpenWrt profile and working peripherals.
- Reuse an existing extraction. A UBI boot volume named `filestruct_full.bin.ubifs` can contain raw FDTs and compressed kernel records, not a mountable UBIFS. Scan validated FDT headers, preserve offsets/hashes, and compare static memory/SMP properties to source; CFE can patch the live handoff, so a static DTB is not the live hardware map.
- Check current public WIP and firmware-patching projects before saying a radio is impossible. Separate an author's claimed hardware result, publicly buildable patches, firmware licensing, host-driver support and exact-band SAE/PMF operation; one does not establish the others.
- Audit VLAN addons for transient failure behavior, not only steady-state bridge membership. A watcher repairing guest VAPs after they rejoin br0, or a quarantine rule that silently degrades when unsupported, is not verified fail-closed isolation.
- For a host-only dtc probe on a minimal fleet worker, unpack the distro package plus `libfdt` and `libyaml` into the job directory, use Python `tarfile` compression detection when the host tar helper fails, and set `LD_LIBRARY_PATH` to those local library directories. Preserve the actual loader/extractor error and rerun on the authorized worker instead of installing system-wide or claiming the dependency is present.
- Keep userland experiments non-bootable: run individual ARM tools with private libraries in a network/filesystem-isolated host probe; never start another init/network manager against the vendor router. QEMU on a modern host proves neither the old vendor-kernel ABI nor device boot/RF behavior.

## Firmware-specific gates
- Reuse a previously hash-verified extraction instead of unpacking again. Broadcom NETGEAR CHKs can concatenate independent JFFS2 namespaces; split at proven boundaries before Jefferson so reused inode IDs do not merge CFE and kernel files. Route reconstructed UBI volumes by magic, not a misleading `.ubifs` suffix.
- Pin the kernel/include tree before compiling a DTS. Labels and paths change between kernel versions (for example BCM4908 NAND labels); compile and inspect the resulting DTB rather than assuming a current-main outline works against an older buildroot.
- Parse vendor kernel wrappers before treating `file: data` as unknown architecture. BCM4908 has a 20-byte little-endian header, `BRCM` at +12 and an LZMA stream at +20; compare load/entry fields without promoting them to a complete safe RAM map.
- Inventory ELF architecture/imports before disassembly. Broadcom ARM64 firmware can ship ARM32 userland; use `llvm-objdump` when host GNU objdump lacks the target. Preserve one disassembly, then inspect exported vendor API calls and constant arguments; do not equate GPIO API arguments with measured physical pins or Linux GPIO numbers.
- Distinguish a compiled kernel/DTB, a CFE RAM-boot-compatible artifact set, a demonstrated hardware boot, and a flashable image. ImageBuilder cannot remove storage drivers from its prebuilt kernel or substitute for an initramfs kernel build; never rename a RAM kernel to a factory image.
- Assert the effective OpenWrt `.config` after `make defconfig`, not only the seed: `TARGET_ROOTFS_INITRAMFS_SEPARATE` requires the target's `FEATURES+=separate_ramdisk` / `USES_SEPARATE_INITRAMFS` gate and is silently dropped without it. Fail before downloads/compilation when required options disappear.
- Reuse version-matched OpenWrt SDK host tools when a modern host compiler breaks an old tool bootstrap. SDK executables may be shell launchers resolving their loader relative to `$0`: test the direct path, then use an absolute-exec wrapper rather than a symlink into another prefix, and smoke-test the installed wrapper before a long build.
- Inventory the external toolchain's runtime libraries and compare `scripts/ext-toolchain.sh --print-libs` before relying on OpenWrt defaults: libc file specs can assume glibc names even for musl. Assert the actual initrd contains the correct ELF machine, executable init and resolvable dynamic loader, not merely a BusyBox filename.
- Check a failed executable's shebang before assuming the file is absent. Minimal fleet mount namespaces can expose `/usr/bin/bash` without `/bin/bash`; an environment-resolved Bash shebang can repair a build helper without changing target functionality. Reproduce the specific package compile before resuming the full build.
- In isolated fleet builds, preserve TLS verification when `/etc/ssl` is absent: explicitly stage a public CA bundle and set SSL_CERT_FILE/CURL_CA_BUNDLE/GIT_SSL_CAINFO. Queue admission delays and prerequisite failures are not measured compiler performance.

## Install (only on request)
`brew install jadx apktool radare2 binwalk wabt wireshark ghidra` · `npm i -g @electron/asar` · `dotnet tool install -g ilspycmd` · `cargo install cargo-audit`.
