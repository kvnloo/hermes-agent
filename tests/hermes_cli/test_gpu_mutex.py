"""Host GPU mutex is exclusive and non-blocking."""

from hermes_cli.gpu_mutex import acquire_gpu_lock, release_gpu_lock


def test_second_nonblocking_acquire_fails(tmp_path):
    lock = tmp_path / "gpu.lock"
    fd1 = acquire_gpu_lock(lock, blocking=False)
    assert fd1 is not None
    fd2 = acquire_gpu_lock(lock, blocking=False)
    assert fd2 is None
    release_gpu_lock(fd1)
    fd3 = acquire_gpu_lock(lock, blocking=False)
    assert fd3 is not None
    release_gpu_lock(fd3)
