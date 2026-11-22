"""
Run a command and store its standard output in a file, touching the file only if the output changed.

This backs `shell` and `run`: they run the command when configuring, and Ninja reruns it through
`python -m bob._capture --output=OUTPUT [--cwd=DIR] [--no-check] [--command-line] -- ARGS...` on every
build, so that Bob reconfigures exactly when the output changes. Both runs go through `execute` here,
so they can't interpret the command differently or see different environments.

This module is internal and deliberately only imports the standard library, to keep startup fast.
"""

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

# What a shell returns for a command that can't be found or run.
FAILED_TO_RUN_RETURNCODE = 127

# Bob sets these for its own output: `FORCE_COLOR` in the regeneration command, and `CLICOLOR_FORCE` and
# `NINJA_STATUS` for pretty Ninja runs. So the configure-time and build-time runs would see different
# values, and a command whose output depends on them would reconfigure forever. Neither run passes them
# on.
REMOVED_ENVIRONMENT_VARIABLES = ("FORCE_COLOR", "CLICOLOR_FORCE", "NINJA_STATUS")


def execute(command: Sequence[str] | str, cwd: Path) -> tuple[int, bytes]:
    """
    Run `command` without a shell, returning its return code and standard output.

    `command` is a list of arguments, or (on Windows) a complete command line that is passed to
    `CreateProcess` as-is. The latter is for `cmd.exe`, which doesn't understand the quoting that
    `subprocess` uses to join a list of arguments.

    The command doesn't see `REMOVED_ENVIRONMENT_VARIABLES`.

    Raises `OSError` if the program can't be run at all (e.g. it doesn't exist).
    """

    env = {
        key: value
        for key, value in os.environ.items()
        if key not in REMOVED_ENVIRONMENT_VARIABLES
    }
    p = subprocess.run(
        command if isinstance(command, str) else list(command),
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        check=False,
    )
    return p.returncode, p.stdout


def store(output: Path, data: bytes) -> None:
    """Write `data` to `output` unless it already contains exactly that."""

    if output.is_file() and output.read_bytes() == data:
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".new")
    temporary.write_bytes(data)
    os.replace(temporary, output)


def main(argv: Sequence[str]) -> int:
    if "--" not in argv:
        print("bob._capture: expected `--` before the command", file=sys.stderr)
        return 2

    separator = list(argv).index("--")
    command = list(argv[separator + 1 :])

    parser = argparse.ArgumentParser(prog="python -m bob._capture", allow_abbrev=False)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cwd", type=Path, default=Path("."))
    parser.add_argument("--no-check", action="store_true")
    parser.add_argument(
        "--command-line",
        action="store_true",
        help="the command is a single, complete command line (see `execute`)",
    )
    options = parser.parse_args(argv[:separator])

    if options.command_line and len(command) != 1:
        parser.error("--command-line expects exactly one command line after `--`")

    try:
        returncode, stdout = execute(
            command[0] if options.command_line else command, options.cwd
        )
    except OSError as error:
        print(f"bob: failed to run {command[0]!r}: {error}", file=sys.stderr)
        returncode, stdout = FAILED_TO_RUN_RETURNCODE, b""

    if returncode != 0 and not options.no_check:
        # Fail the build, leaving the previous output alone.
        return returncode

    store(options.output, stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
