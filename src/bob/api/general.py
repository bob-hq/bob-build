import logging
from typing import Literal, overload

from bob.core.context import Context


@overload
def config(
    name: str, required: Literal[False] = False, default: None = None
) -> None | str: ...


@overload
def config(name: str, required: Literal[False] = False, default: str = "") -> str: ...


@overload
def config(
    name: str, required: Literal[True] = True, default: None | str = None
) -> str: ...


def config(name: str, required: bool = False, default: None | str = None) -> None | str:
    context = Context.current()

    context.used_configs.add(name)

    if name not in context.configs and not required:
        logging.info(f'Unset config "{name}"')
        return default

    return context.configs[name]
