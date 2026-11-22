import shlex
import subprocess
import sys
from collections.abc import Sequence


def quote_args(args: Sequence[str]) -> str:
    """Quote `args` into a command line, the way Ninja runs commands on this platform."""

    if sys.platform == "win32":
        # Ninja runs commands directly with `CreateProcess`.
        return subprocess.list2cmdline(args)

    # Ninja runs commands with `/bin/sh -c`.
    return shlex.join(args)
