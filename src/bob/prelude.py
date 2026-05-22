"""Bob classes, functions and variables that should be used in Bobfiles."""

import inspect
import logging
import subprocess
import sys
from importlib.metadata import version as importlib_version
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, overload

from bob.constants import BOB_BUILD_SUBDIR
from bob.core import (
    Rule,
    Variable,
    phony,
)
from bob.core.context import BobContext
from bob.core.provider import Provider, RuleProvider
from bob.core.rule import RuleInput, SingleRuleInput, rule_input_add, rule_input_resolve
from bob.core.targets import FileTarget, PhonyTarget, RootRelativePath

T = TypeVar("T")


def rule(
    command: str,
    depfile: Optional[str] = None,
    deps: Optional[str] = None,
    compile_command: Optional[str] = None,
    description: Optional[str] = None,
    restat=False,
    generator: Optional[bool] = None,
    pool: Optional[str] = None,
    always=False,
    implicit: Optional[List[str]] = None,
    order_only: Optional[List[str]] = None,
    implicit_outputs: Optional[List[str]] = None,
    **variables,
):
    """
    Create a rule for building targets.
    @param command: The command to run for building, can use $variables.
    @param depfile: A generated dependency file.
    @param deps: The format of the generated dependency file.
    @param compile_command: The command to use in the compilation database, if any.
    @param description: The short description of the rule to show in non-verbose mode.
    @param restat: Whether to restat the outputs after building.
    @param pool: A Ninja pool to use for this rule.
    @param generator: Whether this rule's targets shouldn't be cleaned.
    @param always: Whether to always build any targets built by the rule.
    @param implicit: Implicit dependencies which should be added to every target invocation built by the rule.
    @param order_only: Order-only dependencies which should be added to every target invocation built by the rule.
    @param implicit_outputs: Implicit outputs which should be added to every target invocation built by the rule.
    @param variables: Initial values for variables.
    """

    context = BobContext.get()

    result = Rule(
        command=command,
        depfile=depfile,
        deps=deps,
        compile_command=compile_command,
        description=description,
        restat=restat,
        generator=generator,
        pool=pool,
        always=always,
        implicit=implicit,
        order_only=order_only,
        implicit_outputs=implicit_outputs,
        **variables,
    )

    context.rules.append(result)

    return result


def read(path: Union[RootRelativePath, Path, str]):
    """Reads the file in the given root-relative `path`."""

    if isinstance(path, RootRelativePath):
        path = path.value

    path = Path(path)

    context = BobContext.get()

    context.configure_implicit_dependencies.add(RootRelativePath(path))

    return path.read_bytes()


def glob(pattern: str, path: Union[None, Path, str] = None):
    """Find all files matching the given `pattern` in the given `path`."""

    context = BobContext.get()

    if path is None:
        path = context.current_source_dir
    else:
        path = context.current_source_dir / path

    context.configure_implicit_dependencies.add(path)
    context.configure_implicit_dependencies.update(
        p for p in path.rglob("*") if p.is_dir()
    )

    return [
        Path(f)
        for f in sorted(
            str(f.value.relative_to(context.current_source_dir.value))
            for f in path.glob(pattern)
            if f.is_file()
        )
    ]


def curdir():
    """Returns the root-relative path to the configuration's current directory."""

    context = BobContext.get()

    return RootRelativePath(context.current_source_dir)


def export(**variables: Any):
    """Export variables to anyone calling this file using `subbob`."""

    context = BobContext.get()

    context.exports.update(variables)


@overload
def use(
    name: str, type: Type[T], optional: bool = False, default: Optional[T] = None
) -> T: ...


@overload
def use(
    name: str, type: None = None, optional: bool = False, default: Any = None
) -> Any: ...


def use(
    name: str,
    type: Optional[Type[T]] = None,
    optional: bool = False,
    default: Any = None,
) -> Union[T, Any]:
    """
    Use the given name provided by anyone calling this file using `subbob`.
    @param name: The name of the provided value.
    @param type: An optional class to verify the value is an instance of.
    @param optional: Succeed even if the value wasn't provided.
    @param default: Return this value if the value wasn't provided and `optional` is set.
    """

    context = BobContext.get()

    if optional and name not in context.provides:
        return default

    result = context.provides[name]

    if type is not None and not isinstance(result, type):
        raise TypeError()

    return result


def _get_bobfile(path: Union[str, Path]):
    context = BobContext.get()

    p = (context.current_source_dir / path).value
    if p.is_dir():
        return Path(path), "Bobfile"

    return Path(path).parent, p.name


def subbob(
    path: Union[str, Path],
    configs: Optional[Dict[str, Any]] = None,
    change_build_dir: Union[None, bool, Path] = True,
    **provides,
):
    """
    Execute another Bobfile in a separate scope.
    @param path: The path to the directory containing the Bobfile, or the Bobfile itself (possibly with a different name).
    @param configs: The configs used for the sub-Bobfile.
    @param chdir: Whether to resolve paths relative to the sub-Bobfile's parent directory and build its targets in a sub-directory.
    @param provides: Additional values to provide to the Bobfile, which can consume them with `use`.
    """

    if configs is None:
        configs = {}

    context = BobContext.get()

    context._backup()

    path, bobname = _get_bobfile(path)

    if change_build_dir is True:
        change_build_dir = path

    if change_build_dir:
        context.current_build_dir /= change_build_dir

    context.current_source_dir /= path
    context.configs = configs
    context.exports = {}
    context.provides = provides
    context.unused_configs = set(configs.keys())

    context.configure(bobname)
    result = context.get_exports()
    if len(context.unused_configs) != 0:
        logging.warning(
            f'Unused configs in subbob("{path}"): '
            + ", ".join(f'"{config}"' for config in sorted(context.unused_configs))
        )

    context._restore()

    return result


def include(
    path: Union[str, Path],
    change_build_dir: Union[None, bool, Path] = False,
    change_source_dir: Union[None, bool, Path] = True,
):
    """
    Include the Bobfile in the given path by executing it in the caller's scope.
    @param path: The path to the directory containing the Bobfile, or the Bobfile itself (possibly with a different name).
    @param chdir: Whether to resolve paths relative to the sub-Bobfile's parent directory and build its targets in a sub-directory.
    """

    context = BobContext.get()

    original_source_dir = context.current_source_dir
    original_build_dir = context.current_build_dir

    path, bobname = _get_bobfile(path)
    bobfile = (path / bobname).resolve()

    if change_build_dir is True:
        change_build_dir = path

    if change_build_dir:
        context.current_build_dir /= change_build_dir

    if change_source_dir is True:
        change_source_dir = path

    if change_source_dir:
        context.current_source_dir /= change_source_dir

    frame = inspect.currentframe().f_back
    code = compile(bobfile.read_text("utf-8"), str(bobfile), "exec")
    exec(code, frame.f_globals, frame.f_locals)
    context.configure_implicit_dependencies.add(
        RootRelativePath(bobfile.relative_to(context.root))
    )

    context.current_source_dir = original_source_dir
    context.current_build_dir = original_build_dir


def config(name: str, required=False, default: Optional[str] = None):
    """
    Get a specific config provided in the command line.
    @param name: The name of the config to get.
    @param required: Whether the config must be provided.
    @param default: Return this value if the config isn't set doesn't exist and `required` isn't set.
    """

    context = BobContext.get()

    if name in context.unused_configs:
        context.unused_configs.remove(name)

    if name not in context.configs and not required:
        logging.info(f'Unset config "{name}"')
        return default

    return context.configs[name]


def generate_rule(
    command: str,
    depfile: Optional[str] = None,
    deps: Optional[str] = None,
    compile_command: Optional[str] = None,
    description: Optional[str] = None,
    generator: Optional[bool] = None,
    implicit: Optional[List[str]] = None,
    order_only: Optional[List[str]] = None,
    implicit_outputs: Optional[List[str]] = None,
    **variables,
):
    """Create a rule that always runs the given `command` and stores its output only if it changed."""

    if description is None:
        description = "GEN"

    return rule(
        command=f"(({command}) > $out.new && cmp -s $out $out.new || mv $out.new $out); rm -f $out.new",
        depfile=depfile,
        deps=deps,
        compile_command=compile_command,
        description=description,
        restat=True,
        generator=generator,
        always=True,
        implicit=implicit,
        order_only=order_only,
        implicit_outputs=implicit_outputs,
        **variables,
    )


def shell(
    command: str,
    text=True,
):
    """Run the given shell command during configuration."""

    context = BobContext.get()

    name = BOB_BUILD_SUBDIR / f"bob-shell-{context.shell_index}"
    context.shell_index += 1

    generated: FileTarget = generate_rule(command).build(name)

    context.configure_implicit_dependencies.add(generated.path.value)

    p = subprocess.run(command, shell=True, capture_output=True)
    if p.returncode != 0:
        sys.stdout.buffer.write(p.stdout)
        sys.stderr.buffer.write(p.stderr)
        logging.error(f"Executing {command} failed")
        sys.exit(p.returncode)

    output = p.stdout

    output_file = generated.path.value
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_bytes(output)

    if text:
        output = output.decode()

    return output


def builddir() -> RootRelativePath:
    """Returns the path to the current build directory."""
    context = BobContext.get()

    return context.current_build_dir


def variable(name: str, *rules: Rule):
    """Return an object for modifying the variable called `name` in each of the `rules`."""

    return Variable(*rules, name=name)


def bob_required_version(version: str):
    bob_version = importlib_version("bob")

    major, minor, *rest = map(int, version.split("."))
    bob_major, bob_minor, *rest = map(int, bob_version.split("."))

    if major != bob_major or bob_minor < minor:
        raise Exception(f"Invalid bob version: need {version} but have {bob_version}")


__all__ = [
    "FileTarget",
    "PhonyTarget",
    "RootRelativePath",
    "Provider",
    "RuleProvider",
    "SingleRuleInput",
    "RuleInput",
    "rule_input_add",
    "rule_input_resolve",
    "rule",
    "variable",
    "phony",
    "export",
    "use",
    "curdir",
    "subbob",
    "include",
    "read",
    "glob",
    "config",
    "generate_rule",
    "shell",
    "builddir",
    "bob_required_version",
]
