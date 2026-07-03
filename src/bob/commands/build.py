import os
import subprocess
import sys
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path
from typing import Sequence

from bob.commands.clean import clean
from bob.commands.compdb import compdb
from bob.commands.configure import configure
from bob.constants import get_build_ninja_path
from bob.jobserver import jobserver
from bob.pretty import pretty_run_ninja


def run_ninja(
    builddir: Path,
    targets: Sequence[str] = (),
    no_pretty: bool = False,
    extra_ninja_arguments: None | list[str] = None,
) -> None:
    arguments = [
        "ninja",
        "-f",
        str(get_build_ninja_path(builddir)),
    ]

    if extra_ninja_arguments is not None:
        arguments.extend(extra_ninja_arguments)

    arguments.extend(targets)

    returncode = (
        subprocess.run(arguments).returncode
        if no_pretty
        else pretty_run_ninja(arguments)
    )

    if returncode != 0:
        sys.exit(returncode)


def build(
    builddir: Path,
    bobfile: Path,
    do_clean: bool = False,
    no_compdb: bool = False,
    symlink_compdb: bool = False,
    configs: Sequence[str] = (),
    use_current_configs: bool = False,
    targets: Sequence[str] = (),
    jobs: None | int = None,
    no_jobserver: bool = False,
    no_pretty: bool = False,
    allow_build_outside_builddir: bool = False,
    extra_ninja_arguments: None | list[str] = None,
) -> None:
    if jobs is None:
        jobs = os.cpu_count()

    context: AbstractContextManager[None] = nullcontext()

    if not no_jobserver:
        assert jobs is not None
        context = jobserver(jobs)

    with context:
        if do_clean:
            clean(builddir)

        configure(
            builddir,
            bobfile,
            configs,
            use_current_configs,
            lazy=True,
            allow_build_outside_builddir=allow_build_outside_builddir,
        )

        p: subprocess.Popen[bytes] | None = None
        if not no_compdb:
            p = compdb(
                builddir,
                bobfile,
                dont_symlink=not symlink_compdb,
                use_current_configs=True,
                wait=False,
            )

        run_ninja(builddir, targets, no_pretty, extra_ninja_arguments)

        if p is not None:
            assert p.wait() == 0
