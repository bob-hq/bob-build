import logging
from importlib.metadata import version as importlib_version
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


def bob_required_version(version: str, bob_version: None | str = None) -> None:
    if bob_version is None:
        bob_version = importlib_version("bob-build")

    if "." not in version:
        raise ValueError(
            f"Invalid required version {version} doesn't contain minor requirement!"
        )

    major, minor, *_ = map(int, version.split("."))
    bob_major, bob_minor, *_ = map(int, bob_version.split("."))

    if major != bob_major or bob_minor < minor or (major == 0 and bob_minor != minor):
        raise Exception(f"Invalid bob version: need {version} but have {bob_version}")
