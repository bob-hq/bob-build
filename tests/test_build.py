import json
from pathlib import Path
from textwrap import dedent

import pytest

from bob.commands.build import build
from bob.constants import COMPDB_PATH, get_build_ninja_path
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


def test_build_reconfigures_custom_builddir(bobfile: Path) -> None:
    builddir = Path("custom-build")
    bobfile.write_text(
        dedent("""
            from bob.prelude import *

            Rule("echo v1 > $out").build("x")
        """)
    )

    build(builddir, bobfile)
    assert (builddir / "x").read_text() == "v1\n"

    with assert_modification_time_increases(get_build_ninja_path(builddir)):
        bobfile.write_text(bobfile.read_text().replace("v1", "v2"))
        build(builddir, bobfile)

    assert (builddir / "x").read_text() == "v2\n"
    assert not Path("build").exists()


def test_build_bobfile_in_subdirectory(unique_tmp_path: Path, builddir: Path) -> None:
    bobfile = Path("sub") / "Bobfile"
    bobfile.parent.mkdir()
    bobfile.write_text(
        dedent("""
            from bob.prelude import *

            Rule(f"echo {read('data.txt', text=True).strip()} > $out").build("x")
        """)
    )
    data = Path("sub") / "data.txt"
    data.write_text("v1")

    build(builddir, bobfile)
    assert (builddir / "x").read_text() == "v1\n"

    with assert_modification_time_does_not_change(get_build_ninja_path(builddir)):
        build(builddir, bobfile)

    with assert_modification_time_increases(get_build_ninja_path(builddir)):
        data.write_text("v2")
        build(builddir, bobfile)

    assert (builddir / "x").read_text() == "v2\n"


def test_build_shell_output_rule_failure_fails_build(
    bobfile: Path, builddir: Path
) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *

            shell_output_rule("echo partial; false").build("generated")
        """)
    )

    with pytest.raises(SystemExit) as error:
        build(builddir, bobfile)

    assert error.value.code != 0
    assert not (builddir / "generated").exists()


def test_build_unchecked_shell_does_not_fail_build(
    bobfile: Path, builddir: Path
) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *

            shell("echo output; false", check=False)
        """)
    )

    build(builddir, bobfile)
    build(builddir, bobfile)


@pytest.mark.parametrize("no_jobserver", [False, True])
def test_build_unlimited_jobs(
    bobfile: Path, builddir: Path, no_jobserver: bool
) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *

            Rule("echo hi > $out").build("hi")
        """)
    )

    build(builddir, bobfile, jobs=0, no_jobserver=no_jobserver)
    assert (builddir / "hi").read_text() == "hi\n"


def test_build_compdb_is_up_to_date_after_reconfigure(
    unique_tmp_path: Path, bobfile: Path, builddir: Path
) -> None:
    for name in ("a.c", "b.c"):
        (unique_tmp_path / name).write_text("")

    bobfile.write_text(
        dedent("""
            from bob.prelude import *

            cc = Rule("cp $in $out", compile_command="cc -c $in -o $out", single_input=True)
            cc.build("a.o", inputs=["a.c"])
        """)
    )

    build(builddir, bobfile)
    assert "b.c" not in (builddir / COMPDB_PATH).read_text()

    bobfile.write_text(bobfile.read_text() + 'cc.build("b.o", inputs=["b.c"])\n')
    build(builddir, bobfile)
    assert "b.c" in (builddir / COMPDB_PATH).read_text()


def test_build_shell_with_dollar(
    bobfile: Path, builddir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BOB_TEST_VALUE", "v1")
    bobfile.write_text(
        dedent("""
            from bob.prelude import *

            value = shell("echo $BOB_TEST_VALUE", strip=True)
            Rule(f"echo {value} > $out").build("x")
        """)
    )

    build(builddir, bobfile)
    assert (builddir / "x").read_text() == "v1\n"

    with assert_modification_time_does_not_change(get_build_ninja_path(builddir)):
        build(builddir, bobfile)

    monkeypatch.setenv("BOB_TEST_VALUE", "v2")
    with assert_modification_time_increases(get_build_ninja_path(builddir)):
        build(builddir, bobfile)

    assert (builddir / "x").read_text() == "v2\n"


SHOW_ARGUMENTS_SCRIPT = dedent("""
    import json
    import pathlib
    import sys

    print(json.dumps([sys.argv[1:], pathlib.Path("data.txt").read_text()]))
""")


def test_build_run(unique_tmp_path: Path, bobfile: Path, builddir: Path) -> None:
    arguments = ["a b", "$x", "$$", "'q'", '"d"', ";", "*", "--", ""]

    sub = unique_tmp_path / "sub"
    sub.mkdir()
    (sub / "show.py").write_text(SHOW_ARGUMENTS_SCRIPT)
    (sub / "data.txt").write_text("v1")
    (sub / "Bobfile").write_text(
        dedent(f"""
            import sys
            from pathlib import Path

            from bob.prelude import *

            # Runs in the srcdir (`sub`) by default.
            output = run([sys.executable, Path("show.py"), *{arguments!r}])
            Path("result.json").write_text(output)
        """)
    )
    bobfile.write_text(
        dedent("""
            from bob.prelude import *

            include("sub")
        """)
    )

    build(builddir, bobfile)
    assert json.loads(Path("result.json").read_text()) == [arguments, "v1"]

    # The build-time run must see exactly the same arguments, or it would reconfigure.
    with assert_modification_time_does_not_change(get_build_ninja_path(builddir)):
        build(builddir, bobfile)

    (sub / "data.txt").write_text("v2")
    with assert_modification_time_increases(get_build_ninja_path(builddir)):
        build(builddir, bobfile)

    assert json.loads(Path("result.json").read_text()) == [arguments, "v2"]


def test_build_run_failure_fails_build(
    unique_tmp_path: Path, bobfile: Path, builddir: Path
) -> None:
    bobfile.write_text(
        dedent("""
            import sys

            from bob.prelude import *

            run([sys.executable, "-c", "import pathlib, sys; sys.exit(pathlib.Path('fail').exists())"])
        """)
    )

    build(builddir, bobfile)

    (unique_tmp_path / "fail").write_text("")
    with pytest.raises(SystemExit) as error:
        build(builddir, bobfile)

    assert error.value.code != 0


def test_build_unchecked_run(bobfile: Path, builddir: Path) -> None:
    bobfile.write_text(
        dedent("""
            import sys

            from bob.prelude import *

            assert run([sys.executable, "-c", "print('x'); exit(3)"], check=False) == "x"
            assert run(["bob-test-program-that-does-not-exist"], check=False) == ""
        """)
    )

    build(builddir, bobfile)
    with assert_modification_time_does_not_change(get_build_ninja_path(builddir)):
        build(builddir, bobfile)


@pytest.mark.parametrize(
    ("args", "match"),
    [
        (["bob-test-program-that-does-not-exist"], "Failed to run"),
        (["false"], "exited with return code 1"),
    ],
)
def test_configure_run_failure(
    bobfile: Path, builddir: Path, args: list[str], match: str
) -> None:
    bobfile.write_text(
        dedent(f"""
            from bob.prelude import *

            run({args!r})
        """)
    )

    with pytest.raises(ValueError, match=match):
        build(builddir, bobfile)


# Names that would be taken as flags, split by the shell, or expanded by Ninja or the shell if they
# weren't escaped (with and without spaces, since e.g. `argparse` never takes "-a b" as a flag).
@pytest.mark.parametrize("hostile_name", ["-weird name's $x", "-weird$x"])
def test_build_escapes_everything(
    unique_tmp_path: Path, bobfile: Path, hostile_name: str
) -> None:
    builddir = Path(f"{hostile_name}-build")
    sub = unique_tmp_path / f"{hostile_name}-src"
    sub.mkdir()
    (sub / f"{hostile_name}.txt").write_text("v1")
    (sub / "Bobfile").write_text(
        dedent("""
            import shlex
            import sys
            from pathlib import Path

            from bob.prelude import *

            name = Path(__file__).parent.name.removesuffix("-src")
            data = f"{name}.txt"

            # Bob quotes `$source`, but only the rule's author can stop `cat` taking it as a flag.
            copy = Rule("cat -- $source > $out", variables={"source": Path()})
            # A single `Path` variable is quoted as one argument.
            copy.build(f"{name} copy", implicit=[data], variables={"source": srcdir() / data})
            Rule("cp -- $in $out").build(f"{name} in", inputs=[data])
            shell_output_rule("cat -- $in", single_input=True).build(
                f"{name} shell", inputs=[data]
            )
            run_output = run([sys.executable, "-c", "print(open(sys.argv[1]).read())", data])
            shell_output = shell(f"cat -- {shlex.quote(str(srcdir() / data))}")
            Path("outputs.txt").write_text(f"{run_output}|{shell_output}")
        """).replace(
            "print(open(sys.argv[1]).read())",
            "import sys; print(open(sys.argv[1]).read())",
        )
    )
    # A path starting with `$name` mustn't be taken as a Ninja variable.
    (unique_tmp_path / "$HOME.txt").write_text("home")
    bobfile.write_text(
        dedent(f"""
            from bob.prelude import *

            include({hostile_name + "-src"!r})
            Rule("cp -- $in $out").build("home", inputs=["$HOME.txt"])
        """)
    )

    # Relative, as with `bob build`, so that paths in the root srcdir can start with `$`.
    relative_bobfile = Path(bobfile.name)

    build(builddir, relative_bobfile)
    for suffix in ("copy", "in", "shell"):
        assert (builddir / f"{hostile_name} {suffix}").read_text() == "v1"
    assert Path("outputs.txt").read_text() == "v1|v1"
    assert (builddir / "home").read_text() == "home"
    # Ninja's own `builddir` must be escaped too, or its log would go elsewhere.
    assert (builddir / "bob" / ".ninja_log").is_file()

    with assert_modification_time_does_not_change(get_build_ninja_path(builddir)):
        build(
            builddir, relative_bobfile, targets=[str(builddir / f"{hostile_name} copy")]
        )

    (sub / f"{hostile_name}.txt").write_text("v2")
    with assert_modification_time_increases(get_build_ninja_path(builddir)):
        build(builddir, relative_bobfile)

    for suffix in ("copy", "in", "shell"):
        assert (builddir / f"{hostile_name} {suffix}").read_text() == "v2"
    assert Path("outputs.txt").read_text() == "v2|v2"


def test_build_unknown_target_exits_with_ninja_error(
    bobfile: Path, builddir: Path
) -> None:
    bobfile.write_text(
        dedent("""
            from bob.prelude import *

            Rule("echo hi > $out").build("hi")
        """)
    )

    # Ninja's own error, not the compilation DB failing for the same reason afterwards.
    with pytest.raises(SystemExit) as error:
        build(builddir, bobfile, targets=["nope"])

    assert error.value.code == 1


def test_build_shell_depending_on_color_variables_does_not_reconfigure_forever(
    bobfile: Path, builddir: Path
) -> None:
    # Bob sets `FORCE_COLOR` when reconfiguring and `CLICOLOR_FORCE` for pretty Ninja runs, but
    # the configure-time and build-time runs of a `shell` command must see the same environment.
    bobfile.write_text(
        dedent("""
            import sys

            from bob.prelude import *

            run([sys.executable, "-c", "import os; print(os.environ.get('FORCE_COLOR'), os.environ.get('CLICOLOR_FORCE'))"])
        """)
    )

    build(builddir, bobfile)

    # Reconfigure through Ninja's regeneration command.
    bobfile.write_text(bobfile.read_text() + "\n")
    build(builddir, bobfile)

    with assert_modification_time_does_not_change(get_build_ninja_path(builddir)):
        build(builddir, bobfile)
