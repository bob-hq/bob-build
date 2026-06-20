import os
from pathlib import Path
from textwrap import dedent
from typing import Generator

import pytest

from bob.constants import get_build_ninja_path
from bob.core.context import Context
from bob.prelude import Rule

CASES_PATH = Path(__file__).parent / "cases"


@pytest.fixture()
def builddir() -> Path:
    return Path("build")


@pytest.fixture()
def bobfile(tmp_path: Path) -> Path:
    return tmp_path / "Bobfile"


@pytest.fixture(autouse=True)
def chdir_tmp(tmp_path: Path) -> None:
    os.chdir(tmp_path)


@pytest.fixture()
def context(chdir_tmp, builddir: Path) -> Generator[Context, None, None]:
    with Context(builddir) as context:
        yield context


@pytest.mark.parametrize(
    "case", [case.stem for case in CASES_PATH.iterdir() if case.suffix == ".bob"]
)
def test_configure(pytestconfig: pytest.Config, case: str, builddir: Path) -> None:
    bobfile = (CASES_PATH / f"{case}.bob").resolve()
    expected_ninja_path = CASES_PATH / f"{case}.ninja"

    with Context(builddir) as context:
        context.evaluate(bobfile)

    build_ninja_path = get_build_ninja_path(builddir)

    assert build_ninja_path.is_file()

    actual = build_ninja_path.read_text()

    if pytestconfig.getoption("--update"):
        expected_ninja_path.write_text(actual)
    else:
        expected = expected_ninja_path.read_text()
        assert actual == expected


def test_ninja_removed_when_configure_fails(bobfile: Path, builddir: Path) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *
            
            Rule("echo hi > $out", description="ECHO").build("hi")
            raise Exception("configure exception")
    """)
    )

    with pytest.raises(Exception, match="configure exception"):
        with Context(builddir) as context:
            context.evaluate(bobfile)

    assert not get_build_ninja_path(builddir).exists()


def test_rule_unused_variable_in_constructor(context: Context) -> None:
    with pytest.raises(KeyError, match="dummy"):
        Rule("echo hi > $out", variables={"dummy": "hi"})


def test_rule_unused_variable_in_build(context: Context) -> None:
    rule = Rule("echo hi > $out")
    with pytest.raises(KeyError, match="dummy"):
        rule.build("hi", variables={"dummy": "hi"})


def test_rule_uninitialized_variable(context: Context) -> None:
    rule = Rule("echo $something > $out")
    with pytest.raises(ValueError, match='Variable "something" is uninitialized'):
        rule.build("hi")
