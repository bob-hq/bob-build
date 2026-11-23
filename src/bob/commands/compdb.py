import subprocess
import sys
from collections.abc import Collection
from pathlib import Path

from ninja import BIN_DIR as NINJA_BIN_DIR

from bob.commands.configure import configure
from bob.constants import COMPDB_PATH, get_compdb_ninja_path


def compdb(
    builddir: Path,
    bobfile: Path,
    dont_symlink: bool,
    configs: Collection[str] = (),
    use_current_configs: bool = False,
    targets: Collection[str] = (),
) -> None:
    build_compdb_path = builddir / COMPDB_PATH

    configure(builddir, bobfile, configs, use_current_configs, lazy=True)

    ninja_args = (
        ["-t", "compdb"]
        if len(targets) == 0
        else ["-t", "compdb-targets", "--", *targets]
    )

    # Write to a separate file so that a failure keeps the previous database.
    new_compdb_path = build_compdb_path.with_name(build_compdb_path.name + ".new")
    with new_compdb_path.open("w") as f:
        returncode = subprocess.run(
            [
                Path(NINJA_BIN_DIR) / "ninja",
                "-f",
                get_compdb_ninja_path(builddir),
                *ninja_args,
            ],
            stdout=f,
            check=False,
        ).returncode

    if returncode != 0:
        new_compdb_path.unlink()
        sys.exit(returncode)

    new_compdb_path.replace(build_compdb_path)

    if not dont_symlink:
        COMPDB_PATH.unlink(missing_ok=True)
        COMPDB_PATH.symlink_to(build_compdb_path)
