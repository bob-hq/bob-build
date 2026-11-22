import os
import shlex
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, Literal, TypeAlias, TypeVar, cast, overload

from bob.api.scope import ScopeStack
from bob.api.variable import NINJA_PROVIDED_VARIABLES, Variable
from bob.constants import BOB_BUILDDIR_SUBDIRECTORY
from bob.core.context import Context
from bob.external.ninja_syntax import escape as ninja_escape
from bob.utilities.fills import Template
from bob.utilities.quoting import quote_args


@dataclass(frozen=True)
class FileTarget:
    path: Path


@dataclass(frozen=True)
class PhonyTarget:
    name: str


def _reject_strings(**arguments: object) -> None:
    # `str` is a `Sequence[str]`, so type checkers accept e.g. `inputs="main.c"`, which would
    # otherwise be split into one input per character.
    for name, value in arguments.items():
        if isinstance(value, (str, bytes)):
            raise TypeError(f"`{name}` takes a list, not a single string: {value!r}")


class RuleInput:
    Type: TypeAlias = str | Path | FileTarget | PhonyTarget
    Multiple: TypeAlias = Type | Sequence[Type]

    def __init__(self) -> None:
        raise NotImplementedError("RuleInput is a utility namespace")

    @overload
    @staticmethod
    def resolve(
        value: Type,
        /,
        *,
        srcdir_relative_paths: bool = True,
        convert_strings_to_paths: bool = True,
        path_only: Literal[False] = False,
        convert_to_string: Literal[False] = False,
        single: Literal[True] = True,
    ) -> Path | str: ...

    @overload
    @staticmethod
    def resolve(
        *values: Type,
        srcdir_relative_paths: bool = True,
        convert_strings_to_paths: bool = True,
        path_only: Literal[False] = False,
        convert_to_string: Literal[False] = False,
        single: Literal[False],
    ) -> list[Path | str]: ...

    @overload
    @staticmethod
    def resolve(
        value: Type,
        /,
        *,
        srcdir_relative_paths: bool = True,
        convert_strings_to_paths: bool = True,
        path_only: Literal[True],
        convert_to_string: Literal[False] = False,
        single: Literal[True] = True,
    ) -> Path: ...

    @overload
    @staticmethod
    def resolve(
        *values: Type,
        srcdir_relative_paths: bool = True,
        convert_strings_to_paths: bool = True,
        path_only: Literal[True],
        convert_to_string: Literal[False] = False,
        single: Literal[False],
    ) -> list[Path]: ...

    @overload
    @staticmethod
    def resolve(
        value: Type,
        /,
        *,
        srcdir_relative_paths: bool = True,
        convert_strings_to_paths: bool = True,
        path_only: bool = False,
        convert_to_string: Literal[True],
        single: Literal[True] = True,
    ) -> str: ...

    @overload
    @staticmethod
    def resolve(
        *values: Type,
        srcdir_relative_paths: bool = True,
        convert_strings_to_paths: bool = True,
        path_only: bool = False,
        convert_to_string: Literal[True],
        single: Literal[False],
    ) -> list[str]: ...

    @staticmethod
    def resolve(
        *values: Type,
        srcdir_relative_paths: bool = True,
        convert_strings_to_paths: bool = True,
        path_only: bool = False,
        convert_to_string: bool = False,
        single: bool = True,
    ) -> Path | str | list[str] | list[Path] | list[Path | str]:
        context = Context.current()
        result: list[Path | str] = []

        if single:
            assert len(values) == 1

        for value in values:
            if isinstance(value, str) and convert_strings_to_paths:
                value = Path(value)

            if isinstance(value, Path) and srcdir_relative_paths:
                value = context.current_src_subdir / value

            if isinstance(value, FileTarget):
                value = value.path

            if isinstance(value, PhonyTarget):
                value = value.name

            if path_only and not isinstance(value, Path):
                raise ValueError(f"Failed to resolve {value}")

            if convert_to_string:
                value = str(value)

            if single:
                return value

            result.append(value)

        return result

    @staticmethod
    def id(
        value: Type,
        sep: str = os.path.sep,
    ) -> str:
        context = Context.current()

        if isinstance(value, str):
            value = Path(value)

        if isinstance(value, Path):
            value = context.current_src_subdir / value

        if isinstance(value, Path):
            return sep.join(
                ("src", str(value))
                if not value.is_absolute()
                else ("abssrc", str(value).removeprefix("/"))
            )
        elif isinstance(value, FileTarget):
            value = value.path
            return sep.join(("built", str(value.relative_to(context.builddir))))
        else:
            return sep.join(("phony", value.name))


OutputType = TypeVar("OutputType", bound=FileTarget | list[FileTarget])


class Rule(Generic[OutputType]):
    @overload
    def __init__(
        self: "Rule[FileTarget]",
        command: str,
        *,
        depfile: None | str = None,
        deps: None | str = None,
        description: None | str = None,
        restat: bool = False,
        generator: bool = False,
        pool: None | str = None,
        always: bool = False,
        compile_command: None | str = None,
        single_input: bool = False,
        single_output: Literal[True] = True,
        variables: None | Mapping[str, RuleInput.Multiple] = None,
        implicit: None | Sequence[RuleInput.Type] = None,
        order_only: None | Sequence[RuleInput.Type] = None,
        implicit_outputs: None | Sequence[str | Path] = None,
        rspfile: None | str = None,
        rspfile_content: None | str = None,
    ) -> None: ...

    @overload
    def __init__(
        self: "Rule[list[FileTarget]]",
        command: str,
        *,
        depfile: None | str = None,
        deps: None | str = None,
        description: None | str = None,
        restat: bool = False,
        generator: bool = False,
        pool: None | str = None,
        always: bool = False,
        compile_command: None | str = None,
        single_input: bool = False,
        single_output: Literal[False],
        variables: None | Mapping[str, RuleInput.Multiple] = None,
        implicit: None | Sequence[RuleInput.Type] = None,
        order_only: None | Sequence[RuleInput.Type] = None,
        implicit_outputs: None | Sequence[str | Path] = None,
        rspfile: None | str = None,
        rspfile_content: None | str = None,
    ) -> None: ...

    def __init__(
        self,
        command: str,
        *,
        depfile: None | str = None,
        deps: None | str = None,
        description: None | str = None,
        restat: bool = False,
        generator: bool = False,
        pool: None | str = None,
        always: bool = False,
        compile_command: None | str = None,
        single_input: bool = False,
        single_output: bool = True,
        variables: None | Mapping[str, RuleInput.Multiple] = None,
        implicit: None | Sequence[RuleInput.Type] = None,
        order_only: None | Sequence[RuleInput.Type] = None,
        implicit_outputs: None | Sequence[str | Path] = None,
        rspfile: None | str = None,
        rspfile_content: None | str = None,
    ):
        from bob.api.scoped_value import ScopedValue

        _reject_strings(
            implicit=implicit, order_only=order_only, implicit_outputs=implicit_outputs
        )

        context = Context.current()

        name = f"bob-{context.next_index('rule')}"
        if description is not None:
            # Ninja rule names may only contain ASCII letters, digits, `_`, `.` and `-`.
            name = (
                "".join(c for c in description.lower() if c.isascii() and c.isalnum())
                + "-"
                + name
            )
            description += " $out"

        if variables is None:
            variables = {}

        assert (rspfile is None) == (rspfile_content is None), (
            "When using response files, you must specify both `rspfile` and `rspfile_content`"
        )

        command_template = Template(command)
        depfile_template = Template(depfile) if depfile is not None else None
        description_template = (
            Template(description) if description is not None else None
        )
        compile_command_template = (
            Template(compile_command) if compile_command is not None else None
        )
        rspfile_content_template = (
            Template(rspfile_content) if rspfile_content is not None else None
        )

        variable_names: set[str] = set()
        for template_name, template in (
            ("command", command_template),
            ("depfile", depfile_template),
            ("description", description_template),
            ("compile command", compile_command_template),
            ("rspfile content", rspfile_content_template),
        ):
            if template is None:
                continue

            if not template.is_valid():
                raise ValueError(f"Invalid {template_name}: {template}")

            variable_names.update(template.get_identifiers())

        self.name = name
        self.command = command_template
        self.depfile = Template(depfile) if depfile is not None else None
        self.variable_names = variable_names
        self.variables: dict[str, RuleInput.Multiple] = {}
        self.has_compile_command = compile_command is not None
        self.single_input = single_input
        self.single_output = single_output
        self.always = always
        self.implicit: ScopedValue[list[RuleInput.Type]] = ScopedValue(
            list(implicit or [])
        )
        self.order_only: ScopedValue[list[RuleInput.Type]] = ScopedValue(
            list(order_only or [])
        )
        self.implicit_outputs: ScopedValue[list[str | Path]] = ScopedValue(
            list(implicit_outputs or [])
        )
        self.has_rspfile = rspfile is not None

        for key, value in variables.items():
            self[key].set(value)

        assert context.writer is not None
        assert context.compdb_writer is not None
        context.writer.rule(
            name=name,
            command=command,
            description=description,
            depfile=depfile,
            generator=generator,
            pool=pool,
            restat=restat,
            deps=deps,
            rspfile=rspfile,
            rspfile_content=rspfile_content,
        )
        context.writer.newline()
        if compile_command is not None:
            context.compdb_writer.rule(name=name, command=compile_command)

    def __getitem__(self, name: str) -> Variable:
        return Variable(name, self)

    def build(
        self,
        *outputs: str | Path,
        inputs: None | Sequence[RuleInput.Type] = None,
        implicit: None | Sequence[RuleInput.Type] = None,
        order_only: None | Sequence[RuleInput.Type] = None,
        implicit_outputs: None | Sequence[str | Path] = None,
        pool: None | str = None,
        dyndep: None | str = None,
        variables: None | Mapping[str, RuleInput.Multiple] = None,
    ) -> OutputType:
        _reject_strings(
            inputs=inputs,
            implicit=implicit,
            order_only=order_only,
            implicit_outputs=implicit_outputs,
        )

        if variables is None:
            variables = {}

        if self.single_output and len(outputs) != 1:
            raise ValueError("Expected a single output!")

        if self.single_input and (inputs is None or len(inputs) != 1):
            raise ValueError("Expected a single input!")

        provided_variables = (
            {*NINJA_PROVIDED_VARIABLES, "rspfile"}
            if self.has_rspfile
            else NINJA_PROVIDED_VARIABLES
        )

        with ScopeStack([self[key].set(value) for key, value in variables.items()]):
            for variable in self.variable_names:
                if (
                    variable not in provided_variables
                    and variable not in self.variables
                ):
                    raise ValueError(f'Variable "{variable}" is uninitialized')

            context = Context.current()

            substitution_variables: dict[str, str] = {}
            if self.single_input:
                assert inputs is not None
                substitution_variables["in"] = RuleInput.resolve(
                    inputs[0], convert_to_string=True
                )
            if self.single_output:
                assert outputs is not None
                substitution_variables["out"] = str(
                    context.builddir / context.current_build_subdir / str(outputs[0])
                )

            resolved_outputs = [
                context.builddir / context.current_build_subdir / output
                for output in outputs
            ]
            resolved_implicit_outputs = [
                context.builddir / context.current_build_subdir / implicit_output
                for implicit_output in (implicit_outputs or [])
            ] + [
                Path(Template(p).safe_substitute(substitution_variables))
                if isinstance(p, str)
                else context.builddir / context.current_build_subdir / p
                for p in RuleInput.resolve(
                    *self.implicit_outputs.get(required=True),
                    convert_strings_to_paths=False,
                    single=False,
                    srcdir_relative_paths=False,
                )
            ]

            if not context.allow_build_outside_builddir:
                for output in resolved_outputs + resolved_implicit_outputs:
                    if context.builddir.resolve() not in output.resolve().parents:
                        raise ValueError(
                            f"Refusing to build {output} outside of the build directory"
                        )

            resolved_variables: dict[str, str | list[str] | None] = {
                key: _variable_value(value) for key, value in self.variables.items()
            }

            if self.always:
                assert context.always is not None
                # Don't mutate the caller's list.
                implicit = [*(implicit or []), context.always]

            resolved_inputs = (
                RuleInput.resolve(
                    *inputs,
                    convert_strings_to_paths=True,
                    convert_to_string=True,
                    single=False,
                )
                if inputs is not None
                else None
            )
            resolved_implicit = RuleInput.resolve(
                *(implicit or []),
                convert_strings_to_paths=True,
                convert_to_string=True,
                single=False,
            ) + [
                Template(p).safe_substitute(substitution_variables)
                if isinstance(p, str)
                else str(p)
                for p in RuleInput.resolve(
                    *self.implicit.get(required=True),
                    single=False,
                    convert_strings_to_paths=False,
                )
            ]
            resolved_order_only = RuleInput.resolve(
                *(order_only or []),
                convert_strings_to_paths=True,
                convert_to_string=True,
                single=False,
            ) + [
                Template(p).safe_substitute(substitution_variables)
                if isinstance(p, str)
                else str(p)
                for p in RuleInput.resolve(
                    *self.order_only.get(required=True),
                    single=False,
                    convert_strings_to_paths=False,
                )
            ]
            str_resolved_outputs = [str(output) for output in resolved_outputs]
            str_resolved_implicit_outputs = [
                str(implicit_output) for implicit_output in resolved_implicit_outputs
            ]

            assert context.writer is not None
            assert context.compdb_writer is not None
            context.writer.build(
                outputs=str_resolved_outputs,
                rule=self.name,
                inputs=resolved_inputs,
                implicit=resolved_implicit,
                order_only=resolved_order_only,
                variables=resolved_variables,
                implicit_outputs=str_resolved_implicit_outputs,
                pool=pool,
                dyndep=dyndep,
            )

            if self.has_compile_command:
                context.compdb_writer.build(
                    outputs=str_resolved_outputs,
                    rule=self.name,
                    inputs=resolved_inputs,
                    implicit=resolved_implicit,
                    order_only=resolved_order_only,
                    variables=resolved_variables,
                    implicit_outputs=str_resolved_implicit_outputs,
                    pool=pool,
                    dyndep=dyndep,
                )
            else:
                context.compdb_writer.build(
                    outputs=str_resolved_outputs,
                    rule="phony",
                    inputs=resolved_inputs,
                    implicit=resolved_implicit,
                    order_only=resolved_order_only,
                    implicit_outputs=str_resolved_implicit_outputs,
                )

            if self.single_output:
                return cast(OutputType, FileTarget(resolved_outputs[0]))
            else:
                return cast(
                    OutputType, [FileTarget(output) for output in resolved_outputs]
                )


def _variable_value(value: RuleInput.Multiple) -> str:
    """Render a variable's value for a Ninja command."""

    if isinstance(value, str):
        # A single string is inserted as-is, so that it can hold several arguments.
        return ninja_escape(value)

    # Anything else is a single argument (e.g. a path) or a list of arguments, so quote each one.
    values = [value] if isinstance(value, RuleInput.Type) else value
    return ninja_escape(
        quote_args(
            [
                RuleInput.resolve(
                    v,
                    srcdir_relative_paths=False,
                    convert_strings_to_paths=False,
                    convert_to_string=True,
                )
                for v in values
            ]
        )
    )


def phony(name: str, inputs: None | Sequence[RuleInput.Type] = None) -> PhonyTarget:
    _reject_strings(inputs=inputs)
    context = Context.current()

    resolved_inputs = (
        RuleInput.resolve(
            *inputs,
            convert_strings_to_paths=True,
            convert_to_string=True,
            single=False,
        )
        if inputs is not None
        else None
    )

    assert context.writer is not None
    context.writer.build(
        [name],
        rule="phony",
        inputs=resolved_inputs,
    )

    assert context.compdb_writer is not None
    context.compdb_writer.build([name], rule="phony", inputs=resolved_inputs)

    return PhonyTarget(name)


def shell_output_rule(
    command: str,
    pool: None | str = None,
    single_input: bool = False,
    check: bool = True,
) -> Rule[FileTarget]:
    """
    Always run `command` and store its output, touching the output only when it changed.

    Unless `check` is False, a failing `command` fails the build.
    """

    run = f"({command}) > $out.new"
    if not check:
        run = f"{{ {run}; true; }}"

    return Rule(
        # Ninja shell-quotes `$out` itself (`$out.new` then concatenates); `--` keeps paths from
        # being taken as flags.
        command=f"{run} && {{ cmp -s -- $out $out.new || mv -f -- $out.new $out; }}; status=$$?; rm -f -- $out.new; exit $$status",
        description="SHELL",
        restat=True,
        pool=pool,
        always=True,
        single_input=single_input,
    )


def _shell_args(command: str) -> list[str] | str:
    """
    The arguments that run `command` with the system shell, like `subprocess` with `shell=True`.

    On Windows, this is a complete command line rather than a list (see `bob._capture.execute`).
    """

    if sys.platform == "win32":
        # Exactly what `subprocess` builds for `shell=True`: `cmd.exe` takes everything after `/c`
        # literally, so `command`'s own quotes must not be escaped.
        return f'{os.environ.get("COMSPEC", "cmd.exe")} /c "{command}"'

    # `--` so that a command starting with `-` isn't taken as options of the shell.
    return ["/bin/sh", "-c", "--", command]


def _capture(
    args: list[str] | str,
    cwd: Path,
    display: str,
    description: str,
    check: bool,
    text: bool,
    strip: bool,
) -> str | bytes:
    """
    Run `args` now and on every build, reconfiguring whenever its output changes.

    `args` is a list of arguments, or a complete command line (see `bob._capture.execute`).

    Both runs go through `bob._capture`, and `args` are escaped for Ninja, so they're identical.
    """

    from bob import _capture as capture

    if len(args) == 0:
        raise ValueError("Expected a command to run!")

    if any("\n" in arg for arg in ([args] if isinstance(args, str) else args)):
        raise ValueError(f"Ninja can't run commands containing newlines: {display!r}")

    context = Context.current()

    name = BOB_BUILDDIR_SUBDIRECTORY / f"bob-shell-output-{context.next_index('shell')}"
    output_path = context.builddir / context.current_build_subdir / name

    # Option values are attached with `=` so that they can't be taken as options themselves.
    capture_args = [
        sys.executable,
        "-m",
        "bob._capture",
        f"--cwd={cwd}",
        f"--output={output_path}",
        *([] if check else ["--no-check"]),
        *(["--command-line", "--", args] if isinstance(args, str) else ["--", *args]),
    ]
    generated = Rule(
        ninja_escape(quote_args(capture_args)),
        description=description,
        restat=True,
        always=True,
    ).build(name)

    context.configure_implicit_dependencies.add(generated)

    try:
        returncode, output = capture.execute(args, cwd)
    except OSError as error:
        if check:
            raise ValueError(f"Failed to run {display!r}: {error}") from error
        returncode, output = capture.FAILED_TO_RUN_RETURNCODE, b""

    if check and returncode != 0:
        sys.stdout.buffer.write(output)
        raise ValueError(f'"{display}" exited with return code {returncode}')

    capture.store(generated.path, output)

    if strip:
        output = output.strip()

    if text:
        return output.decode()

    return output


@overload
def shell(
    command: str, text: Literal[True] = True, check: bool = True, strip: bool = False
) -> str: ...


@overload
def shell(
    command: str, text: Literal[False], check: bool = True, strip: bool = False
) -> bytes: ...


# TODO: change strip to True by default in 0.2
def shell(
    command: str, text: bool = True, check: bool = True, strip: bool = False
) -> str | bytes:
    """
    Run `command` with the system shell from the root directory, and return its output.

    Bob reruns `command` on every build, and reconfigures whenever its output changes.
    Unless `check` is False, the command failing is an error. The command doesn't see `FORCE_COLOR`,
    `CLICOLOR_FORCE` or `NINJA_STATUS`, which Bob sets for its own output.
    """

    return _capture(
        _shell_args(command),
        cwd=Path("."),
        display=command,
        description="SHELL",
        check=check,
        text=text,
        strip=strip,
    )


@overload
def run(
    args: Sequence[str | os.PathLike[str]],
    *,
    text: Literal[True] = True,
    check: bool = True,
    strip: bool = True,
    cwd: None | str | os.PathLike[str] = None,
) -> str: ...


@overload
def run(
    args: Sequence[str | os.PathLike[str]],
    *,
    text: Literal[False],
    check: bool = True,
    strip: bool = True,
    cwd: None | str | os.PathLike[str] = None,
) -> bytes: ...


def run(
    args: Sequence[str | os.PathLike[str]],
    *,
    text: bool = True,
    check: bool = True,
    strip: bool = True,
    cwd: None | str | os.PathLike[str] = None,
) -> str | bytes:
    """
    Run the program `args[0]` with the arguments `args[1:]` without a shell, and return its output.

    Arguments are passed as-is, so they need no quoting. The command runs in `cwd`, which is
    relative to the srcdir and defaults to it. Like `shell`, Bob reruns the command on every build
    and reconfigures whenever its output changes, and unless `check` is False, the command failing
    is an error. Like with `shell`, the command doesn't see `FORCE_COLOR`, `CLICOLOR_FORCE` or
    `NINJA_STATUS`.
    """

    if isinstance(args, (str, bytes)):
        raise TypeError(
            "`run` takes a list of arguments, use `shell` to run a command line"
        )

    resolved_args = [os.fspath(arg) for arg in args]
    resolved_cwd = Context.current().current_src_subdir / (cwd or ".")

    return _capture(
        resolved_args,
        cwd=resolved_cwd,
        display=shlex.join(resolved_args),
        description="RUN",
        check=check,
        text=text,
        strip=strip,
    )
