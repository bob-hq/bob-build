import os
from pathlib import Path
from textwrap import dedent

import pytest

from bob.constants import get_build_ninja_path
from bob.core.configure import configure

CASES_PATH = Path(__file__).parent / "cases"


@pytest.mark.parametrize(
    "case", [case.stem for case in CASES_PATH.iterdir() if case.suffix == ".bob"]
)
def test_configure(pytestconfig: pytest.Config, tmp_path: Path, case: str) -> None:
    bobfile = CASES_PATH / f"{case}.bob"
    expected_ninja_path = CASES_PATH / f"{case}.ninja"

    os.chdir(tmp_path)
    builddir = Path("build")
    configure(builddir, bobfile.resolve())

    build_ninja_path = get_build_ninja_path(builddir)

    assert build_ninja_path.is_file()

    actual = build_ninja_path.read_text()

    if pytestconfig.getoption("--update"):
        expected_ninja_path.write_text(actual)
    else:
        expected = expected_ninja_path.read_text()
        assert actual == expected


def test_ninja_removed_when_configure_fails(tmp_path: Path) -> None:
    os.chdir(tmp_path)
    bobfile = tmp_path / "Bobfile"
    bobfile.write_text(
        dedent("""
            from bob.prelude import *
            
            Rule("echo hi > $out", description="ECHO").build("hi")
            raise Exception("")
    """)
    )

    builddir = Path("build")

    with pytest.raises(Exception):
        configure(builddir, bobfile)

    assert not get_build_ninja_path(builddir).exists()
