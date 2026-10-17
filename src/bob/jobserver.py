import os
import sys
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from bob.external import jobserver_pool


@contextmanager
def jobserver(jobs: int) -> Generator[None]:
    if jobs <= 0:
        raise ValueError("Cannot run a jobserver with non-positive jobs!")

    if sys.platform == "win32" or sys.platform == "cygwin":
        import win32api

        # Run with a Window semaphore.
        handle, env = jobserver_pool.create_sem(
            "jobserver_pool",
            jobs,
        )
        try:
            os.environ["MAKEFLAGS"] = env["MAKEFLAGS"]
            yield
        finally:
            del os.environ["MAKEFLAGS"]
            win32api.CloseHandle(handle)
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            fifo_path = tmpdir_path / "jobserver"

            read_fd = None
            write_fd = None
            try:
                read_fd, write_fd, env = jobserver_pool.create_fifo(
                    str(fifo_path), jobs
                )
                os.environ["MAKEFLAGS"] = env["MAKEFLAGS"]
                yield
            finally:
                del os.environ["MAKEFLAGS"]
                if read_fd is not None:
                    os.close(read_fd)
                if write_fd is not None:
                    os.close(write_fd)
                os.remove(fifo_path)
