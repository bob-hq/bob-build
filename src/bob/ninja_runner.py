import os
import subprocess
from collections.abc import Iterable
from pathlib import Path

from ninja import BIN_DIR as NINJA_BIN_DIR

from bob.constants import get_build_ninja_path
from bob.pretty import pretty_run_ninja

NINJA_PATH = Path(NINJA_BIN_DIR) / "ninja"


def run_ninja(
    builddir: Path,
    targets: Iterable[os.PathLike[str] | str] = (),
    no_pretty: bool = False,
    extra_ninja_arguments: None | list[str] = None,
    jobs: None | int = None,
    hide_no_work: bool = False,
) -> int:
    """Run Ninja on the build directory's manifest and return its exit code."""

    arguments: list[os.PathLike[str] | str] = [
        NINJA_PATH,
        "-f",
        str(get_build_ninja_path(builddir)),
    ]

    if jobs is not None:
        arguments.extend(["-j", str(jobs)])

    if extra_ninja_arguments is not None:
        arguments.extend(extra_ninja_arguments)

    targets = list(targets)
    if len(targets) != 0:
        # So that targets starting with `-` aren't taken as options.
        arguments.append("--")
        arguments.extend(targets)

    if no_pretty:
        return subprocess.run(arguments, check=False).returncode

    return pretty_run_ninja(arguments, hide_no_work=hide_no_work)


def regenerate_manifest(builddir: Path, no_pretty: bool = False) -> int:
    """Let Ninja reconfigure the project if anything the manifest depends on changed."""

    manifest = get_build_ninja_path(builddir)
    return run_ninja(builddir, [manifest], no_pretty=no_pretty, hide_no_work=True)
