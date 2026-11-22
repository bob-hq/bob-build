import os
import sys
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from bob.external import jobserver_pool


@contextmanager
def _makeflags(value: str) -> Generator[None]:
    """Set MAKEFLAGS for the duration of the context, restoring any previous value."""

    previous = os.environ.get("MAKEFLAGS")
    os.environ["MAKEFLAGS"] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("MAKEFLAGS", None)
        else:
            os.environ["MAKEFLAGS"] = previous


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
            with _makeflags(env["MAKEFLAGS"]):
                yield
        finally:
            win32api.CloseHandle(handle)
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            fifo_path = Path(tmpdir) / "jobserver"

            read_fd, write_fd, env = jobserver_pool.create_fifo(str(fifo_path), jobs)
            try:
                with _makeflags(env["MAKEFLAGS"]):
                    yield
            finally:
                os.close(read_fd)
                os.close(write_fd)
                # The temporary directory removes the FIFO itself.
