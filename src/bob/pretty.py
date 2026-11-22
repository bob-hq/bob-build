import math
import os
import shlex
import subprocess
import sys
from pathlib import PurePath, PurePosixPath, PureWindowsPath
from typing import IO

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)
from rich.text import Text

from bob.constants import BOB_BUILDDIR_SUBDIRECTORY
from bob.log import console

PRETTY_SEPARATOR = " BOB_NINJA_SEPARATOR "
DESCRIPTION_WIDTH = 10

PRETTY_COLORS = (
    "yellow",
    "blue",
    "green",
    "magenta",
    "cyan",
    "bright_yellow",
    "bright_blue",
    "bright_green",
    "bright_magenta",
    "bright_cyan",
)


NINJA_OUTPUT_BLACKLIST = {"ninja: Jobserver mode detected"}
NINJA_NO_WORK = "ninja: no work to do."

HIDDEN_OUTPUT_PREFIX = "bob-shell-output-"


def _is_hidden_status(outputs: str, windows: bool = sys.platform == "win32") -> bool:
    """Whether a status line is for the internal output of a `shell` or `run` command.

    Only their progress lines are hidden, so that their failures are still shown.
    """

    # Their edges have a single output, which Ninja quotes when needed.
    path: PurePath
    if windows:
        # Ninja quotes Windows paths in `"` only when they need it, and `\` is a separator there
        # rather than an escape.
        if len(outputs) >= 2 and outputs[0] == outputs[-1] == '"':
            outputs = outputs[1:-1]
        path = PureWindowsPath(outputs)
    else:
        try:
            parts = shlex.split(outputs)
        except ValueError:
            return False
        if len(parts) != 1:
            return False
        path = PurePosixPath(parts[0])

    return (
        path.name.startswith(HIDDEN_OUTPUT_PREFIX)
        and path.parent.name == BOB_BUILDDIR_SUBDIRECTORY.name
    )


def pretty_run_ninja(
    arguments: list[os.PathLike[str] | str], hide_no_work: bool = False
) -> int:
    env = os.environ.copy()
    env["NINJA_STATUS"] = f"%f,%t{PRETTY_SEPARATOR}"
    env["CLICOLOR_FORCE"] = "1"

    p = subprocess.Popen(
        arguments, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env
    )
    assert p.stdout is not None
    stdout: IO[bytes] = p.stdout

    with Progress(
        SpinnerColumn(),
        MofNCompleteColumn(),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    ) as progress:
        task_id = progress.add_task("", total=None)
        while line := stdout.readline():
            try:
                decoded = line.decode().removeprefix("\n").removesuffix("\n")
            except UnicodeDecodeError:
                sys.stdout.buffer.write(line)
                continue

            if any(b in decoded for b in NINJA_OUTPUT_BLACKLIST):
                continue

            if hide_no_work and decoded == NINJA_NO_WORK:
                continue

            try:
                parameters, _, command = decoded.strip().partition(PRETTY_SEPARATOR)
                finished_edges, total_edges = [int(x) for x in parameters.split(",")]
            except ValueError:
                console.print(decoded, highlight=False, markup=False)
                continue

            progress.update(
                task_id,
                completed=finished_edges,
                total=total_edges,
            )

            description, _, outputs = command.partition(" ")

            if _is_hidden_status(outputs):
                continue

            color = (
                PRETTY_COLORS[ord(description[0]) % len(PRETTY_COLORS)]
                if description
                else PRETTY_COLORS[0]
            )

            outputs = " " + outputs

            available = max(console.width - DESCRIPTION_WIDTH, 0)
            if available < len(outputs):
                if available <= 3:
                    outputs = outputs[:available]
                else:
                    available -= 3
                    outputs = (
                        outputs[: available // 2]
                        + "..."
                        + outputs[-math.ceil(available / 2) :]
                    )

            console.print(
                Text(description.ljust(DESCRIPTION_WIDTH), style=color)
                + Text(outputs, style="white"),
                highlight=False,
                markup=False,
            )

    return p.wait()
