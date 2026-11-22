import os
import sys
from collections.abc import Generator, Sequence
from pathlib import Path
from typing import Any, cast

import pytest

from bob.api.general import bob_required_version, config
from bob.api.path import build_in, builddir, glob, rootdir, src_in, srcdir
from bob.api.rule import FileTarget, Rule, RuleInput, phony, run
from bob.api.scoped_value import ScopedRule, ScopedValue
from bob.commands.configure import configure
from bob.constants import get_build_ninja_path
from bob.core.context import Context
from bob.jobserver import jobserver
from bob.pretty import _is_hidden_status


@pytest.fixture()
def context(unique_tmp_path: Path, builddir: Path) -> Generator[Context]:
    with Context(builddir, Path("Bobfile"), {}, False) as context:
        yield context


def test_rule_unused_variable_in_constructor(context: Context) -> None:
    with pytest.raises(KeyError, match="dummy"):
        Rule("echo hi > $out", variables={"dummy": "hi"})


def test_rule_unused_variable_in_build(context: Context) -> None:
    rule: Rule[FileTarget] = Rule("echo hi > $out")
    with pytest.raises(KeyError, match="dummy"):
        rule.build("hi", variables={"dummy": "hi"})


def test_rule_uninitialized_variable(context: Context) -> None:
    rule: Rule[FileTarget] = Rule("echo $something > $out")
    with pytest.raises(ValueError, match='Variable "something" is uninitialized'):
        rule.build("hi")


def test_glob(unique_tmp_path: Path, context: Context) -> None:
    for f in (
        unique_tmp_path / "dummy" / "inside" / "a.txt",
        unique_tmp_path / "another" / "fun.txt",
        unique_tmp_path / "outside.txt",
        unique_tmp_path / "dummy" / "a.c",
    ):
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"")

    assert glob("**/*.txt", "dummy") == [Path("dummy/inside/a.txt")]
    assert glob("**/*.c") == [Path("dummy/a.c")]


def test_always_rule_does_not_mutate_implicit(context: Context) -> None:
    rule: Rule[FileTarget] = Rule("echo hi > $out", always=True)
    implicit: list[RuleInput.Type] = ["in.txt"]

    rule.build("a", implicit=implicit)
    rule.build("b", implicit=implicit)

    assert implicit == ["in.txt"]


def test_scoped_rule_explicit_variables_take_precedence(context: Context) -> None:
    scoped = ScopedRule(Rule("echo $v > $out", variables={"v": "rule"}))
    explicit: dict[str, RuleInput.Multiple] = {"v": "explicit"}

    with scoped["v"].set("scoped"):
        scoped.build("out", variables=explicit)

    assert explicit == {"v": "explicit"}
    assert context.writer is not None
    context.writer.output.flush()
    assert "  v = explicit\n" in get_build_ninja_path(context.builddir).read_text()


@pytest.mark.parametrize("name", ["description", "pool", "in", "out", "command"])
def test_special_variable_names_are_rejected(context: Context, name: str) -> None:
    with pytest.raises(ValueError, match="special Ninja variable"):
        Rule(f"echo ${name} > $out", variables={name: "x"})


def test_variable_add_rejects_mismatched_kinds(context: Context) -> None:
    rule: Rule[FileTarget] = Rule("echo $v > $out", variables={"v": ["a"]})

    with rule["v"].add(["b"]):
        assert rule["v"].get() == ["a", "b"]

    with pytest.raises(TypeError):
        rule["v"].add("b")

    with pytest.raises(TypeError, match='Cannot add .* to variable "v"'):
        # Untyped code can pass a single path rather than a list.
        rule["v"].add(cast(Any, Path("c")))


def test_scoped_value_get_types(context: Context) -> None:
    value: ScopedValue[list[str]] = ScopedValue()

    assert value.get(required=False) is None
    assert value.get(required=False, default=["d"]) == ["d"]
    with pytest.raises(ValueError):
        value.get()

    with value.set(["x"]):
        # Statically typed as `list[str]`, not `None | list[str]`.
        required: list[str] = value.get()
        assert required == ["x"]


def test_rule_inputs_accept_narrower_sequences(context: Context) -> None:
    cc = Rule("cc -c $in -o $out", single_input=True)
    link = Rule("cc $in -o $out $libs", variables={"libs": []})

    sources: list[Path] = [Path("a.c"), Path("b.c")]
    objects: list[FileTarget] = [
        cc.build(f"{source.stem}.o", inputs=[source]) for source in sources
    ]
    libs: dict[str, str] = {"libs": "-lm"}

    assert link.build("app", inputs=objects, variables=libs).path == Path("build/app")
    phony("objects", objects)
    link.build("app2", inputs=sources, variables={"libs": sources})


def test_required_config_error(context: Context) -> None:
    with pytest.raises(KeyError, match="-c MISSING="):
        config("MISSING", required=True)


@pytest.mark.parametrize(
    ("actual", "ok"),
    [
        ("0.1.12", True),
        ("0.1.12.post1", True),
        ("0.1.12+local", True),
        ("0.1.13.dev1", True),
        ("0.1.12.dev1", False),
        ("0.1.12rc1", False),
        ("0.1.12rc1.post1", False),
        ("0.1.12.post1.dev1", True),
        ("0.1.11", False),
        ("0.2.0", False),
    ],
)
def test_required_version_parsing(actual: str, ok: bool) -> None:
    if ok:
        bob_required_version("0.1.12", actual)
    else:
        with pytest.raises(ValueError):
            bob_required_version("0.1.12", actual)


def test_jobserver_restores_makeflags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAKEFLAGS", "-k")

    with jobserver(2):
        assert "--jobserver-auth" in os.environ["MAKEFLAGS"]

    assert os.environ["MAKEFLAGS"] == "-k"


def test_configure_rejects_malformed_config(builddir: Path, bobfile: Path) -> None:
    with pytest.raises(ValueError, match="KEY=VALUE"):
        configure(builddir, bobfile, ["DEBUG"])


@pytest.mark.parametrize(
    ("srcdir_path", "expected"),
    [(".", "."), ("a/b", "../.."), ("../x", None)],
)
def test_rootdir(
    unique_tmp_path: Path, context: Context, srcdir_path: str, expected: None | str
) -> None:
    with src_in(srcdir_path):
        if expected is None:
            expected = f"../{unique_tmp_path.name}"
        assert rootdir() == Path(expected)
        assert (srcdir() / rootdir()).resolve() == unique_tmp_path.resolve()

    with src_in(unique_tmp_path / "abs"):
        assert rootdir() == Path("..")


def test_combined_scopes_are_not_leaked(context: Context) -> None:
    before = len(context.scopes)

    with build_in("a") | build_in("b") | (build_in("c") | build_in("d")):
        assert builddir() == Path("build/a/b/c/d")

    assert builddir() == Path("build")
    assert len(context.scopes) == before


def test_combined_scopes_close_independently(context: Context) -> None:
    rule = Rule("echo $x $y > $out", variables={"x": "0", "y": "0"})
    before = len(context.scopes)

    with rule["x"].set("1") as x:
        combined = x | rule["y"].set("2")
        assert (rule["x"].get(), rule["y"].get()) == ("1", "2")
    # Exiting `x` closes it although it's also part of `combined`.
    assert (rule["x"].get(), rule["y"].get()) == ("0", "2")

    combined.close()
    assert (rule["x"].get(), rule["y"].get()) == ("0", "0")
    assert len(context.scopes) == before


def test_single_strings_are_rejected_as_lists(context: Context) -> None:
    rule = Rule("cp $in $out", single_input=True)

    with pytest.raises(TypeError, match="inputs"):
        rule.build("out", inputs=cast(Any, "a"))

    with pytest.raises(TypeError, match="implicit"):
        Rule("touch $out").build("out", implicit=cast(Any, "main.c"))

    with pytest.raises(TypeError, match="implicit_outputs"):
        Rule("touch $out").build("out", implicit_outputs=cast(Any, "out.d"))

    with pytest.raises(TypeError, match="order_only"):
        Rule("touch $out", order_only=cast(Any, "main.c"))

    with pytest.raises(TypeError, match="inputs"):
        phony("all", cast(Any, "main.c"))


def test_rootdir_across_drives(
    context: Context, monkeypatch: pytest.MonkeyPatch
) -> None:
    def relpath(path: str, start: str) -> str:
        raise ValueError("path is on mount 'C:', start on mount 'D:'")

    monkeypatch.setattr(os.path, "relpath", relpath)
    assert rootdir() == Path.cwd()


def test_run_rejects_invalid_commands(context: Context) -> None:
    with pytest.raises(TypeError, match="use `shell`"):
        # `str` is a `Sequence[str]`, so only the runtime check can catch this.
        run("echo hi")

    with pytest.raises(ValueError, match="newlines"):
        run(["echo", "a\nb"])

    with pytest.raises(ValueError, match="Expected a command"):
        run([])


def test_paths_with_newlines_are_rejected(context: Context) -> None:
    with pytest.raises(ValueError, match="newlines"):
        Rule("touch $out").build("a\nb")


def test_shell_on_windows_passes_the_command_line_as_is(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bob.api.rule import _shell_args  # pyright: ignore[reportPrivateUsage]

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("COMSPEC", "C:\\Windows\\system32\\cmd.exe")

    # Like `subprocess` with `shell=True`: the inner quotes must reach `cmd.exe` unescaped.
    assert (
        _shell_args('"C:\\Program Files\\x.exe" "a b"')
        == 'C:\\Windows\\system32\\cmd.exe /c ""C:\\Program Files\\x.exe" "a b""'
    )


def test_capture_command_line_is_executed_as_is(
    unique_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bob import _capture as capture

    executed: list[Sequence[str] | str] = []

    def execute(command: Sequence[str] | str, cwd: Path) -> tuple[int, bytes]:
        executed.append(command)
        return 0, b"out"

    monkeypatch.setattr(capture, "execute", execute)
    output = unique_tmp_path / "output"

    assert (
        capture.main([f"--output={output}", "--command-line", "--", 'x /c "a "b""'])
        == 0
    )
    assert executed == ['x /c "a "b""']
    assert output.read_bytes() == b"out"

    with pytest.raises(SystemExit):
        capture.main([f"--output={output}", "--command-line", "--", "a", "b"])


def test_capture_hides_variables_bob_sets_for_its_own_output(
    unique_tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bob import _capture as capture

    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.setenv("CLICOLOR_FORCE", "1")
    monkeypatch.setenv("NINJA_STATUS", "x")
    monkeypatch.setenv("BOB_TEST_VALUE", "kept")

    returncode, output = capture.execute(
        [
            sys.executable,
            "-c",
            (
                "import os; print(sorted(k for k in os.environ if k in "
                "('FORCE_COLOR', 'CLICOLOR_FORCE', 'NINJA_STATUS', 'BOB_TEST_VALUE')))"
            ),
        ],
        unique_tmp_path,
    )

    assert returncode == 0
    assert output.decode().strip() == "['BOB_TEST_VALUE']"


@pytest.mark.parametrize(
    ("outputs", "hidden"),
    [
        ("bob/bob-shell-output-1", True),
        ("build/bob/bob-shell-output-2", True),
        ("'out dir/bob/bob-shell-output-3'", True),
        ("out.txt", False),
        ("build/bob-shell-output-1", False),
        ("bob/bob-shell-output-1 bob/bob-shell-output-2", False),
    ],
)
def test_hidden_status_lines(outputs: str, hidden: bool) -> None:
    assert _is_hidden_status(outputs, windows=False) == hidden


@pytest.mark.parametrize(
    ("outputs", "hidden"),
    [
        ("build\\bob\\bob-shell-output-1", True),
        ("C:\\b\\bob\\bob-shell-output-1", True),
        ('"C:\\my build\\bob\\bob-shell-output-1"', True),
        ("build\\out.txt", False),
    ],
)
def test_hidden_status_lines_on_windows(outputs: str, hidden: bool) -> None:
    assert _is_hidden_status(outputs, windows=True) == hidden
