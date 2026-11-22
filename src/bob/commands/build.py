import os
import sys
from collections.abc import Collection
from contextlib import AbstractContextManager, nullcontext
from pathlib import Path

from bob.commands.clean import clean
from bob.commands.compdb import CompdbError, compdb
from bob.commands.configure import configure
from bob.constants import get_build_ninja_path
from bob.jobserver import jobserver
from bob.ninja_runner import run_ninja


def build(
    builddir: Path,
    bobfile: Path,
    do_clean: bool = False,
    no_compdb: bool = False,
    symlink_compdb: bool = False,
    configs: Collection[str] = (),
    use_current_configs: bool = False,
    targets: Collection[str] = (),
    jobs: None | int = None,
    no_jobserver: bool = False,
    no_pretty: bool = False,
    allow_build_outside_builddir: bool = False,
    extra_ninja_arguments: None | list[str] = None,
) -> None:
    if jobs is None:
        jobs = os.cpu_count() or 1

    if jobs < 0:
        raise ValueError("The number of jobs must not be negative!")

    # A jobserver can't express "unlimited" (0 jobs), so leave that to Ninja itself.
    use_jobserver = not no_jobserver and jobs > 0

    context: AbstractContextManager[None] = (
        jobserver(jobs) if use_jobserver else nullcontext()
    )

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

        returncode = run_ninja(
            builddir,
            targets,
            no_pretty,
            extra_ninja_arguments,
            # With a jobserver, Ninja takes its job slots from it.
            jobs=None if use_jobserver else jobs,
        )

        # Ninja may have reconfigured (regenerating `compdb.ninja`), so only create the compilation
        # DB afterwards. Do so even if the build failed, unless reconfiguring itself failed.
        if not no_compdb and get_build_ninja_path(builddir).exists():
            try:
                compdb(
                    builddir,
                    bobfile,
                    dont_symlink=not symlink_compdb,
                    use_current_configs=True,
                    targets=targets,
                    regenerate=False,
                )
            except CompdbError:
                # When the build failed, the compilation DB is best effort: it fails for the same
                # reason (e.g. an unknown target), which Ninja has already reported.
                if returncode == 0:
                    raise

    if returncode != 0:
        sys.exit(returncode)
