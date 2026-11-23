from pathlib import Path
from textwrap import dedent

import pytest

from bob.commands.build import build
from bob.constants import get_build_ninja_path
from tests.utilities import (
    assert_modification_time_does_not_change,
    assert_modification_time_increases,
)


def test_build_lazy_glob(unique_tmp_path: Path, bobfile: Path, builddir: Path) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *

            glob("**/*.c", "dummy")
        """)
    )

    for f in (
        unique_tmp_path / "dummy" / "inside" / "a.txt",
        unique_tmp_path / "another" / "fun.txt",
        unique_tmp_path / "outside.txt",
        unique_tmp_path / "dummy" / "a.c",
    ):
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"")

    build(builddir, bobfile)

    with (
        assert_modification_time_does_not_change(get_build_ninja_path(builddir)),
    ):
        build(builddir, bobfile)

    (unique_tmp_path / "dummy" / "inside" / "sheesh.c").write_bytes(b"")

    with (
        assert_modification_time_increases(get_build_ninja_path(builddir)),
    ):
        build(builddir, bobfile)


def test_build_always(bobfile: Path, builddir: Path) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *
            
            Rule("echo hi > $out", always=True).build("hi")
    """)
    )

    build(builddir, bobfile)
    assert (builddir / "hi").read_text() == "hi\n"

    with (
        assert_modification_time_increases(builddir / "hi"),
    ):
        build(builddir, bobfile)
        assert (builddir / "hi").read_text() == "hi\n"


def test_build_shell_output_rule(
    unique_tmp_path: Path, bobfile: Path, builddir: Path
) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *
            
            built_magic = shell_output_rule("cat magic").build("magic")
            Rule("cp $in $out").build("copied_magic", inputs=[built_magic])
    """)
    )

    magic_path = unique_tmp_path / "magic"
    magic_path.write_text("initial magic")

    built_magic_path = builddir / "magic"
    copied_magic_path = builddir / "copied_magic"

    build(builddir, bobfile)
    assert (
        built_magic_path.read_text() == copied_magic_path.read_text() == "initial magic"
    )

    with (
        assert_modification_time_does_not_change(built_magic_path),
        assert_modification_time_does_not_change(copied_magic_path),
    ):
        build(builddir, bobfile)
        assert (
            built_magic_path.read_text()
            == copied_magic_path.read_text()
            == "initial magic"
        )

    magic_path.write_text("modified magic")

    with (
        assert_modification_time_increases(built_magic_path),
        assert_modification_time_increases(copied_magic_path),
    ):
        build(builddir, bobfile)
        assert (
            built_magic_path.read_text()
            == copied_magic_path.read_text()
            == "modified magic"
        )


def test_build_shell(unique_tmp_path: Path, bobfile: Path, builddir: Path) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *
            
            output = shell("cat magic")
            Rule(f"echo {output} > $out").build("magic")
    """)
    )

    magic_path = unique_tmp_path / "magic"
    magic_path.write_text("initial magic")

    built_magic_path = builddir / "magic"

    build(builddir, bobfile)
    assert built_magic_path.read_text() == "initial magic\n"

    with (
        assert_modification_time_does_not_change(built_magic_path),
        assert_modification_time_does_not_change(get_build_ninja_path(builddir)),
    ):
        build(builddir, bobfile)
        assert built_magic_path.read_text() == "initial magic\n"

    magic_path.write_text("modified magic")

    with (
        assert_modification_time_increases(built_magic_path),
        assert_modification_time_increases(get_build_ninja_path(builddir)),
    ):
        build(builddir, bobfile)
        assert built_magic_path.read_text() == "modified magic\n"


def test_build_glob_doesnt_break_after_deleted_folders(
    unique_tmp_path: Path, bobfile: Path, builddir: Path
) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *
            
            glob("**/*.txt", "src")
    """)
    )

    dummy_path = unique_tmp_path / "src" / "dummy"
    dummy_path.mkdir(parents=True)

    build(builddir, bobfile)
    assert get_build_ninja_path(builddir).is_file()

    dummy_path.rmdir()

    with (
        assert_modification_time_increases(get_build_ninja_path(builddir)),
    ):
        build(builddir, bobfile)


def test_build_quotes_single_path_variable(
    unique_tmp_path: Path, bobfile: Path, builddir: Path
) -> None:
    bobfile.write_text(
        dedent("""
            from pathlib import Path

            from bob.prelude import *

            Rule("cat $source > $out", description="CAT").build(
                "copied.txt", variables={"source": Path("with space.txt")}
            )
        """)
    )
    (unique_tmp_path / "with space.txt").write_text("contents\n")

    build(builddir, bobfile)

    assert (builddir / "copied.txt").read_text() == "contents\n"


@pytest.mark.parametrize(("jobs", "no_jobserver"), [(0, False), (2, True)])
def test_build_jobs(
    bobfile: Path, builddir: Path, jobs: int, no_jobserver: bool
) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *

            Rule("echo hi > $out").build("hi")
        """)
    )

    build(builddir, bobfile, jobs=jobs, no_jobserver=no_jobserver)

    assert (builddir / "hi").read_text() == "hi\n"


def test_build_unchecked_failing_shell(bobfile: Path, builddir: Path) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *

            shell("echo hi; exit 1", check=False)
        """)
    )

    build(builddir, bobfile)

    with assert_modification_time_does_not_change(get_build_ninja_path(builddir)):
        build(builddir, bobfile)


def test_build_failing_shell_output_rule(bobfile: Path, builddir: Path) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *

            shell_output_rule("exit 1", check=True).build("out")
        """)
    )

    with pytest.raises(SystemExit):
        build(builddir, bobfile)

    assert not (builddir / "out").exists()


def test_build_input_starting_with_dollar(builddir: Path) -> None:
    bobfile = Path("Bobfile")
    Path("$HOME").write_text("hi\n")
    bobfile.write_text(
        dedent("""
            from bob.prelude import *

            Rule("cp $in $out").build("out", inputs=["$HOME"])
        """)
    )

    build(builddir, bobfile)

    assert (builddir / "out").read_text() == "hi\n"


def test_build_shows_failing_shell(
    unique_tmp_path: Path,
    bobfile: Path,
    builddir: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *

            shell("[ -f flag ] && exit 1 || true")
        """)
    )

    build(builddir, bobfile)
    (unique_tmp_path / "flag").touch()
    capsys.readouterr()

    with pytest.raises(SystemExit):
        build(builddir, bobfile)

    assert (
        capsys.readouterr().out.splitlines()[0]
        == "\x1b[31mFAILED: [code=1] \x1b[0mbuild/bob/bob-shell-output-1 "
    )


def test_build_target_starting_with_dash(bobfile: Path) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *

            shell_output_rule("echo hi").build("-out")
        """)
    )

    build(Path("."), bobfile, targets=["-out"])

    assert Path("-out").read_text() == "hi\n"
