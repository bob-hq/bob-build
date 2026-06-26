from pathlib import Path
from typing import Literal, overload

from bob.api.rule import RuleInput
from bob.api.scope import AttributeScope, Scope
from bob.core.context import Context


def build_in(path: str | Path) -> Scope:
    context = Context.current()
    return AttributeScope(
        context, {"current_build_subdir": context.current_build_subdir / path}
    )


def src_in(path: str | Path) -> Scope:
    context = Context.current()
    return AttributeScope(
        context, {"current_src_subdir": context.current_src_subdir / path}
    )


def builddir() -> Path:
    context = Context.current()
    return context.current_build_subdir


def srcdir() -> Path:
    context = Context.current()
    return context.current_src_subdir


@overload
def read(path: RuleInput.Type, text: Literal[True] = True) -> str: ...
@overload
def read(path: RuleInput.Type, text: Literal[False] = False) -> bytes: ...


def read(path: RuleInput.Type, text: bool = False) -> str | bytes:
    path = RuleInput.resolve(path, path_only=True)

    context = Context.current()
    context.configure_implicit_dependencies.add(path)

    if text:
        return path.read_text()

    return path.read_bytes()


def glob(pattern: str, path: None | str | Path = None) -> list[Path]:
    context = Context.current()

    if path is None:
        path = Path(".")

    if isinstance(path, str):
        path = Path(path)

    context.configure_implicit_dependencies.add(path)
    context.configure_implicit_dependencies.update(
        p for p in path.rglob("*") if p.is_dir()
    )

    return sorted(
        path.glob(pattern),
        key=lambda p: str(p),
    )
