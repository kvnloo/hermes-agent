"""Preserve Windows file security before publishing a local existing-file edit.

For an owner/group/DACL that the caller cannot copy, fail before os.replace;
never replace first and attempt to restore an unprivileged owner's SID later.
Remote backends and new files continue through the existing shell writer.
"""

import ctypes
from ctypes import wintypes
import os
import shutil
import stat
import tempfile
from typing import Optional

_SECURITY_INFO = 0x1 | 0x2 | 0x4  # owner, primary group, DACL + returned control flags


def _security_descriptor(path: str) -> bytes:
    api = ctypes.WinDLL("advapi32", use_last_error=True)
    get = api.GetFileSecurityW
    get.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p,
                    wintypes.DWORD, ctypes.POINTER(wintypes.DWORD))
    get.restype = wintypes.BOOL
    needed = wintypes.DWORD()
    get(path, _SECURITY_INFO, None, 0, ctypes.byref(needed))
    if not needed.value:
        raise ctypes.WinError(ctypes.get_last_error())
    buffer = ctypes.create_string_buffer(needed.value)
    if not get(path, _SECURITY_INFO, buffer, len(buffer), ctypes.byref(needed)):
        raise ctypes.WinError(ctypes.get_last_error())
    return buffer.raw[:needed.value]


def _set_security(path: str, descriptor: bytes) -> None:
    api = ctypes.WinDLL("advapi32", use_last_error=True)
    set_file = api.SetFileSecurityW
    set_file.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p)
    set_file.restype = wintypes.BOOL
    buffer = ctypes.create_string_buffer(descriptor)
    if not set_file(path, _SECURITY_INFO, buffer):
        raise ctypes.WinError(ctypes.get_last_error())


def atomic_write(path: str, data: bytes) -> Optional[str]:
    """Stage bytes and original security metadata, verifying both before replace."""
    target = os.path.realpath(path) if os.path.islink(path) else path
    tmp = None
    try:
        descriptor = _security_descriptor(target)
        original = os.stat(target)
        fd, tmp = tempfile.mkstemp(prefix=".hermes-tmp.",
                                   dir=os.path.dirname(target) or ".")
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        shutil.copystat(target, tmp)
        _set_security(tmp, descriptor)
        if _security_descriptor(tmp) != descriptor:
            raise OSError("staged owner, group, DACL or control flags differ")
        current = os.stat(target)
        if ((current.st_ino, current.st_size, current.st_mtime_ns) !=
                (original.st_ino, original.st_size, original.st_mtime_ns)
                or _security_descriptor(target) != descriptor):
            raise OSError("target changed while the replacement was staged")
        os.replace(tmp, target)
        tmp = None
        return None
    except OSError as exc:
        return f"Cannot preserve Windows file security before atomic replace: {exc}"
    finally:
        if tmp is not None:
            try:
                os.chmod(tmp, stat.S_IWRITE)
                os.unlink(tmp)
            except OSError:
                pass
