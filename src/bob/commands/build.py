import os
import subprocess
from contextlib import nullcontext
from pathlib import Path
from typing import Sequence

from bob.commands.clean import clean
from bob.commands.compdb import compdb
from bob.commands.configure import configure
from bob.constants import get_build_ninja_path
from bob.jobserver import jobserver


def run_ninja(builddir: Path, targets: Sequence[str] = ()) -> None:
    arguments = [
        "ninja",
        "-f",
        str(get_build_ninja_path(builddir)),
        *targets,
    ]

    subprocess.run(arguments, check=True)


def build(
    builddir: Path,
    bobfile: Path,
    do_clean=False,
    no_compdb=False,
    symlink_compdb=False,
    configs: Sequence[str] = (),
    use_current_configs=False,
    targets: Sequence[str] = (),
    jobs: None | int = None,
    no_jobserver=False,
) -> None:
    if jobs is None:
        jobs = os.cpu_count()

    context = nullcontext()

    if not no_jobserver:
        assert jobs is not None
        context = jobserver(jobs)

    with context:
        if do_clean:
            clean(builddir)

        configure(builddir, bobfile, configs, use_current_configs, lazy=True)

        p: subprocess.Popen | None
        if not no_compdb:
            p = compdb(
                builddir,
                bobfile,
                dont_symlink=not symlink_compdb,
                use_current_configs=True,
                wait=False,
            )

        run_ninja(builddir, targets)

        if p is not None:
            assert p.wait() == 0
