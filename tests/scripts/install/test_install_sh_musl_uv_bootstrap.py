"""install.sh bootstraps musl uv when the native userland is musl (#123682)."""

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.platforms("linux")

ROOT = Path(__file__).resolve().parents[3]


def test_musl_elf_interpreter_selects_musl_uv_even_when_ldd_says_glibc():
    # The ELF interpreter of /bin/sh decides, as in pm/store.py; a glibc ldd
    # (musl installed as a secondary toolchain, or a gcompat shim) must not.
    script = r"""
source "$1" --manifest >/dev/null
uname() { case "$1" in -m) echo x86_64 ;; -s) echo Linux ;; esac; }
head() { printf '\177ELF\0\0\0/lib/ld-musl-x86_64.so.1\0'; }
ldd() { echo "ldd (GNU libc) 2.39"; }
target="$(uv_bootstrap_target)"
uv_bootstrap_pin "$target"
printf '%s\n%s\n%s\n' "$target" "$UV_PIN_URL" "$UV_PIN_SHA256"
"""
    result = subprocess.run(
        ["bash", "-c", script, "_", str(ROOT / "scripts" / "install.sh")],
        check=True, capture_output=True, text=True,
    )
    row = json.loads((ROOT / "pm" / "lock.json").read_text())["packages"]["uv"]["artifacts"]["linux-x64-musl"]
    assert result.stdout.splitlines() == ["linux-x64-musl", row["url"], row["sha256"]]


def test_late_glibc_interpreter_survives_musl_toolchain(tmp_path):
    """The installer must not select musl when glibc PT_INTERP is beyond 8 KiB."""
    import os
    import struct

    offset = 0x10A000  # Fedora 44 /usr/bin/bash
    loader = b"/lib64/ld-linux-x86-64.so.2\0"
    image = bytearray(offset + len(loader))
    image[:16] = b"\x7fELF" + bytes((2, 1, 1)) + bytes(9)
    image[16:64] = struct.pack("<HHIQQQIHHHHHH", 3, 0, 1, 0, 64, 0, 0, 64, 56, 1, 0, 0, 0)
    image[64:120] = struct.pack("<IIQQQQQQ", 3, 4, offset, 0, 0, len(loader), len(loader), 1)
    image[offset:] = loader
    binary = tmp_path / "bash"
    binary.write_bytes(image)

    # Inject the real parser's verdict for the fixed /bin/sh and /bin/ls probes.
    # The prefix and libc-tool fallbacks remain the installer's real code.
    script = r"""
source "$1" --manifest >/dev/null
uname() { case "$1" in -m) echo x86_64 ;; -s) echo Linux ;; esac; }
head() {
    if [[ "$1" == -c && "$2" == 8192 ]]; then
        command head -c 8192 "$ELF_FIXTURE"
    else
        command head "$@"
    fi
}
ldd() { echo "unavailable"; }
compgen() { return 0; }  # Secondary /lib/ld-musl loader installed
if declare -F _elf_interp_libc >/dev/null; then
    native="$(_elf_interp_libc "$ELF_FIXTURE")" || exit 73
    [[ "$native" == glibc ]] || exit 74
    _elf_interp_libc() { printf '%s\n' "$native"; }
fi
uv_bootstrap_target
"""
    result = subprocess.run(
        ["bash", "-c", script, "_", str(ROOT / "scripts" / "install.sh")],
        env={**os.environ, "ELF_FIXTURE": str(binary)},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "linux-x64"
