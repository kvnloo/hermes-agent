"""Atomic staging and publication of backup output files."""

import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Optional


@contextmanager
def _atomic_output_path(final_path: Path, publish_path: Optional[Callable[[], Optional[Path]]] = None):
    """Yield a hidden sibling path and publish it only after a clean close.

    ``publish_path`` picks the destination at publish time (default ``final_path``) so a caller
    can divert an incomplete archive elsewhere without ever touching ``final_path``; returning
    ``None`` discards the partial instead of publishing it.
    """
    partial_path = final_path.with_name(f".{final_path.name}.{os.getpid()}-{threading.get_ident()}.partial")
    partial_path.unlink(missing_ok=True)
    try:
        yield partial_path
        destination = publish_path() if publish_path else final_path
        if destination is None:
            partial_path.unlink(missing_ok=True)
        else:
            os.replace(partial_path, destination)
    except BaseException:
        partial_path.unlink(missing_ok=True)
        raise
