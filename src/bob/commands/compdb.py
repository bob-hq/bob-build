import subprocess
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
    wait: bool = True,
    targets: Collection[str] = (),
) -> subprocess.Popen[bytes]:
    build_compdb_path = builddir / COMPDB_PATH

    configure(builddir, bobfile, configs, use_current_configs, lazy=True)

    ninja_args = (
        ["-t", "compdb"] if len(targets) == 0 else ["-t", "compdb-targets", *targets]
    )
    with build_compdb_path.open("w") as f:
        p = subprocess.Popen(
            [
                Path(NINJA_BIN_DIR) / "ninja",
                "-f",
                get_compdb_ninja_path(builddir),
                *ninja_args,
            ],
            stdout=f,
        )

        if not dont_symlink:
            COMPDB_PATH.unlink(missing_ok=True)
            COMPDB_PATH.symlink_to(build_compdb_path)

        if wait:
            assert p.wait() == 0

        return p
