import shutil
from logging import getLogger
from pathlib import Path

from bob.constants import BOB_BUILDDIR_SUBDIRECTORY, COMPDB_PATH


def clean(builddir: Path, force: bool = False) -> None:
    if not builddir.exists():
        return

    if not force and not (builddir / BOB_BUILDDIR_SUBDIRECTORY).exists():
        getLogger(__name__).warning(
            f"Not deleting {builddir} since it doesn't seem to be a Bob build directory!"
        )
        return

    if (
        COMPDB_PATH.is_symlink()
        and Path(builddir).resolve() == COMPDB_PATH.resolve().parent
    ):
        COMPDB_PATH.unlink(missing_ok=True)

    shutil.rmtree(builddir)
