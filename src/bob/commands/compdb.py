import subprocess
from pathlib import Path
from typing import Sequence

from bob.commands.configure import configure
from bob.constants import COMPDB_PATH, get_compdb_ninja_path


def compdb(
    builddir: Path,
    bobfile: Path,
    dont_symlink: bool,
    configs: Sequence[str] = (),
    use_current_configs=False,
    wait=True,
) -> subprocess.Popen:
    build_compdb_path = builddir / COMPDB_PATH

    configure(builddir, bobfile, configs, use_current_configs, lazy=True)

    p = subprocess.Popen(
        f"ninja -f {get_compdb_ninja_path(builddir)} -t compdb > {build_compdb_path}",
        shell=True,
    )

    if not dont_symlink:
        COMPDB_PATH.unlink(missing_ok=True)
        COMPDB_PATH.symlink_to(build_compdb_path)

    if wait:
        assert p.wait() == 0

    return p
