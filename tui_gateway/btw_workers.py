"""Live cancellation handles only; thread history lives in the canonical session DB."""
import os
import threading

import psutil

workers = {}
worker_lock = threading.RLock()


def worker_identity():
    return {"pid": os.getpid(), "started": psutil.Process().create_time()}


def worker_alive(identity, turn_id):
    try:
        proc = psutil.Process(identity["pid"])
        return (proc.create_time() == identity["started"]
                and (proc.pid != os.getpid() or turn_id in workers))
    except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
        return False
