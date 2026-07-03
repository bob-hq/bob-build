import os
import subprocess
import sys

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


NINJA_OUTPUT_BLACKLIST = {
    f"/{BOB_BUILDDIR_SUBDIRECTORY}/bob-shell-output-",
    "ninja: Jobserver mode detected",
}


def pretty_run_ninja(arguments: list[str]) -> int:
    env = os.environ.copy()
    env["NINJA_STATUS"] = f"%f,%t{PRETTY_SEPARATOR}"
    env["CLICOLOR_FORCE"] = "1"

    p = subprocess.Popen(
        arguments, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env
    )
    assert p.stdout is not None

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
        while line := p.stdout.readline():
            assert isinstance(line, bytes)

            try:
                decoded = line.decode().removeprefix("\n").removesuffix("\n")
            except UnicodeDecodeError:
                sys.stdout.buffer.write(line)
                continue

            if any(b in decoded for b in NINJA_OUTPUT_BLACKLIST):
                continue

            try:
                parameters, _, command = decoded.strip().partition(PRETTY_SEPARATOR)
                finished_edges, total_edges = [int(x) for x in parameters.split(",")]
            except ValueError:
                console.print(decoded, highlight=False, markup=False)
                continue

            description, _, outputs = command.partition(" ")

            color = PRETTY_COLORS[ord(description[0]) % len(PRETTY_COLORS)]

            console.print(
                Text(description.ljust(DESCRIPTION_WIDTH), style=color)
                + Text(" " + outputs, style="white"),
                highlight=False,
                markup=False,
            )

            progress.update(
                task_id,
                completed=finished_edges,
                total=total_edges,
            )

    return p.wait()
