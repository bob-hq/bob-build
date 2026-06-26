import inspect
import runpy
from pathlib import Path
from typing import Any

from bob.api.scope import AttributeScope
from bob.core.context import Context


def include(path: str | Path) -> None:
    context = Context.current()
    bobfile = context.current_src_subdir / path
    assert bobfile.is_file(), f"Can't include {path}: not found at {bobfile}"
    context.configure_implicit_dependencies.add(bobfile)

    current = inspect.currentframe()
    assert current is not None

    caller = current.f_back
    assert caller is not None

    with AttributeScope(context, {"current_src_subdir": bobfile.parent}):
        caller.f_globals.update(
            runpy.run_path(str(bobfile), caller.f_globals | caller.f_locals)
        )


def subbob(
    path: str | Path, configs: None | dict[str, str] = None, **imports: Any
) -> dict[str, Any]:
    if configs is None:
        configs = {}

    context = Context.current()

    if (context.current_src_subdir / path).is_dir():
        bobfile = context.current_src_subdir / path / "Bobfile"
    else:
        bobfile = context.current_src_subdir / path

    assert bobfile.is_file(), f"Can't subbob {path}: not found at {bobfile}"

    subbob_index = context.variables.get("subbob_index", 1)
    context.variables["subbob_index"] = subbob_index + 1

    subbob_name = f".subbob-{subbob_index}"

    if bobfile.name != "Bobfile":
        subbob_name += f"-{bobfile.stem}"
    else:
        subbob_name += f"-{bobfile.parent.name}"

    with AttributeScope(
        context,
        {
            "current_src_subdir": bobfile.parent,
            "current_build_subdir": Path(subbob_name),
            "imports": imports,
            "exports": {},
            "configs": configs,
        },
    ):
        scopes_before = len(context.scopes)
        context.evaluate(bobfile)
        for scope in reversed(context.scopes[scopes_before:]):
            scope.close()
        return context.exports


def export(**exports: Any) -> None:
    context = Context.current()

    context.exports.update(exports)


def use(name: str, required: bool = True, default: Any = None) -> Any:
    context = Context.current()

    if context.imports is None:
        raise Exception("Cannot `use` outside of a subbob!")

    if name not in context.imports and not required:
        return default

    return context.imports[name]
