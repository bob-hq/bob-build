import subprocess
import sys
from collections.abc import Collection
from pathlib import Path

from bob.commands.configure import configure
from bob.constants import COMPDB_PATH, get_build_ninja_path, get_compdb_ninja_path
from bob.ninja_runner import NINJA_PATH, regenerate_manifest


class CompdbError(RuntimeError):
    """Ninja failed to create the compilation DB."""


def compdb(
    builddir: Path,
    bobfile: Path,
    dont_symlink: bool,
    configs: Collection[str] = (),
    use_current_configs: bool = False,
    targets: Collection[str] = (),
    regenerate: bool = True,
    no_pretty: bool = False,
) -> None:
    """
    Create a compilation database for the project.

    Unless `regenerate` is False, an existing configuration is first brought up to date, since the
    compilation DB is created from the configuration rather than by building.
    """

    build_compdb_path = builddir / COMPDB_PATH
    already_configured = get_build_ninja_path(builddir).exists()

    configure(builddir, bobfile, configs, use_current_configs, lazy=True)

    if regenerate and already_configured:
        returncode = regenerate_manifest(builddir, no_pretty=no_pretty)
        if returncode != 0:
            sys.exit(returncode)

    ninja_args = (
        ["-t", "compdb"]
        if len(targets) == 0
        else ["-t", "compdb-targets", "--", *targets]
    )
    p = subprocess.run(
        [NINJA_PATH, "-f", get_compdb_ninja_path(builddir), *ninja_args],
        capture_output=True,
        check=False,
    )
    if p.returncode != 0:
        message = p.stderr.decode(errors="replace").strip()
        raise CompdbError(
            f"Creating the compilation DB failed with exit code {p.returncode}"
            + (f": {message}" if message else "")
        )

    # Only replace the previous compilation DB once the new one was successfully created.
    build_compdb_path.write_bytes(p.stdout)

    if not dont_symlink:
        COMPDB_PATH.unlink(missing_ok=True)
        COMPDB_PATH.symlink_to(build_compdb_path)
