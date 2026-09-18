import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, Literal, TypeAlias, TypeVar, overload

from ninja.ninja_syntax import escape as ninja_escape

from bob.api.scope import ScopeStack
from bob.api.variable import NINJA_PROVIDED_VARIABLES, Variable
from bob.constants import BOB_BUILDDIR_SUBDIRECTORY
from bob.core.context import Context
from bob.utilities.fills import Template


@dataclass(frozen=True)
class FileTarget:
    path: Path


@dataclass(frozen=True)
class PhonyTarget:
    name: str


class RuleInput:
    Type: TypeAlias = str | Path | FileTarget | PhonyTarget
    Multiple: TypeAlias = Type | list[Type]

    def __init__(self) -> None:
        raise Exception("RuleInput is a utility namespace")

    @overload
    @staticmethod
    def resolve(
        *values: Type,
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
        single: Literal[False] = False,
    ) -> list[Path | str]: ...

    @overload
    @staticmethod
    def resolve(
        *values: Type,
        srcdir_relative_paths: bool = True,
        convert_strings_to_paths: bool = True,
        path_only: Literal[True] = True,
        convert_to_string: Literal[False] = False,
        single: Literal[True] = True,
    ) -> Path: ...

    @overload
    @staticmethod
    def resolve(
        *values: Type,
        srcdir_relative_paths: bool = True,
        convert_strings_to_paths: bool = True,
        path_only: Literal[True] = True,
        convert_to_string: Literal[False] = False,
        single: Literal[False] = False,
    ) -> list[Path]: ...

    @overload
    @staticmethod
    def resolve(
        *values: Type,
        srcdir_relative_paths: bool = True,
        convert_strings_to_paths: bool = True,
        path_only: Literal[False] = False,
        convert_to_string: Literal[True] = True,
        single: Literal[True] = True,
    ) -> str: ...

    @overload
    @staticmethod
    def resolve(
        *values: Type,
        srcdir_relative_paths: bool = True,
        convert_strings_to_paths: bool = True,
        path_only: Literal[True] = True,
        convert_to_string: Literal[True] = True,
        single: Literal[True] = True,
    ) -> str: ...

    @overload
    @staticmethod
    def resolve(
        *values: Type,
        srcdir_relative_paths: bool = True,
        convert_strings_to_paths: bool = True,
        path_only: Literal[False] = False,
        convert_to_string: Literal[True] = True,
        single: Literal[False] = False,
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


OutputType = TypeVar("OutputType", FileTarget, list[FileTarget])


class Rule(Generic[OutputType]):
    @overload
    def __new__(
        cls,
        command: str,
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
        variables: None | dict[str, RuleInput.Multiple] = None,
    ) -> "Rule[FileTarget]": ...

    @overload
    def __new__(
        cls,
        command: str,
        depfile: None | str = None,
        deps: None | str = None,
        description: None | str = None,
        restat: bool = False,
        generator: bool = False,
        pool: None | str = None,
        always: bool = False,
        compile_command: None | str = None,
        single_input: bool = False,
        single_output: Literal[False] = False,
        variables: None | dict[str, RuleInput.Multiple] = None,
    ) -> "Rule[list[FileTarget]]": ...

    def __new__(
        cls,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        return super().__new__(
            cls,
        )

    def __init__(
        self,
        command: str,
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
        variables: None | dict[str, RuleInput.Multiple] = None,
        implicit: None | list[RuleInput.Type] = None,
        order_only: None | list[RuleInput.Type] = None,
        implicit_outputs: None | list[str | Path] = None,
        rspfile: None | str = None,
        rspfile_content: None | str = None,
    ):
        from bob.api.scoped_value import ScopedValue

        context = Context.current()

        rule_index = context.variables.get("rule_index", 1)
        context.variables["rule_index"] = rule_index + 1

        name = f"bob-{rule_index}"
        if description is not None:
            name = "".join(c for c in description.lower() if c.isalnum()) + "-" + name
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
        self.implicit = ScopedValue(implicit or [])
        self.order_only = ScopedValue(order_only or [])
        self.implicit_outputs = ScopedValue(implicit_outputs or [])
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
        inputs: None | list[RuleInput.Type] = None,
        implicit: None | list[RuleInput.Type] = None,
        order_only: None | list[RuleInput.Type] = None,
        implicit_outputs: None | list[str | Path] = None,
        pool: None | str = None,
        dyndep: None | str = None,
        variables: None | dict[str, RuleInput.Multiple] = None,
    ) -> OutputType:
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

            resolved_variables = {
                key: shlex.join(
                    ninja_escape(
                        RuleInput.resolve(
                            v,
                            srcdir_relative_paths=False,
                            convert_strings_to_paths=False,
                            convert_to_string=True,
                        )
                    )
                    for v in value
                )
                if not isinstance(value, str)
                and not isinstance(value, Path)
                and not isinstance(value, FileTarget)
                and not isinstance(value, PhonyTarget)
                else ninja_escape(
                    RuleInput.resolve(
                        value,
                        srcdir_relative_paths=False,
                        convert_strings_to_paths=False,
                        convert_to_string=True,
                    )
                )
                for key, value in self.variables.items()
            }

            if self.always:
                implicit = implicit or []
                assert context.always is not None
                implicit.append(context.always)

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
                return FileTarget(resolved_outputs[0])  # type: ignore[return-value] # ty: ignore[invalid-return-type]
            else:
                return [FileTarget(output) for output in resolved_outputs]  # type: ignore[return-value] # ty: ignore[invalid-return-type]


def phony(name: str, inputs: None | list[RuleInput.Type] = None) -> PhonyTarget:
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
    command: str, pool: None | str = None, single_input: bool = False
) -> Rule[FileTarget]:
    return Rule(
        command=f"(({command}) > $out.new && cmp -s $out $out.new || mv $out.new $out); rm -f $out.new",
        description="SHELL",
        restat=True,
        pool=pool,
        always=True,
        single_input=single_input,
    )


@overload
def shell(
    command: str, text: Literal[True] = True, check: bool = True, strip: bool = False
) -> str: ...


@overload
def shell(
    command: str, text: Literal[False] = False, check: bool = True, strip: bool = False
) -> bytes: ...


# TODO: change strip to True by default in 0.2
def shell(
    command: str, text: bool = True, check: bool = True, strip: bool = False
) -> str | bytes:
    context = Context.current()

    shell_index = context.variables.get("shell_index", 1)
    context.variables["shell_index"] = shell_index + 1

    name = BOB_BUILDDIR_SUBDIRECTORY / f"bob-shell-output-{shell_index}"

    generated = shell_output_rule(command).build(name)

    context.configure_implicit_dependencies.add(generated)

    p = subprocess.run(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if check and p.returncode != 0:
        sys.stdout.buffer.write(p.stdout)
        sys.stderr.buffer.write(p.stderr)
        raise ValueError(f'"{command}" exited with return code {p.returncode}')

    output = p.stdout
    output_file = generated.path.resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_bytes(output)

    if strip:
        output = output.strip()

    if text:
        return output.decode()

    return output
