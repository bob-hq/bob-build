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


# TODO: remove _version in 0.2
def bob_required_package_version(
    package: str, version: str, _actual: None | str = None
) -> None:
    if _actual is None:
        _actual = importlib_version(package)

    if "." not in version:
        raise ValueError(
            f"Invalid required version {version} doesn't contain minor requirement!"
        )

    required_major, required_minor, *required_rest = map(int, version.split("."))
    actual_major, actual_minor, actual_patch = map(int, _actual.split("."))

    if required_major == 0:
        assert len(required_rest) == 1, (
            f'For major 0 you must specify patch version as well, e.g. "0.{required_minor}.X", got: "{version}"'
        )
    else:
        assert len(required_rest) == 0, (
            f'For non-zero major {required_major} you must not specify patch version, e.g. "{required_major}.{required_minor}", got: "{version}"'
        )

    if (
        required_major != actual_major
        or actual_minor < required_minor
        or (
            required_major == 0
            and (actual_minor != required_minor or actual_patch < required_rest[0])
        )
    ):
        raise Exception(f"Invalid {package} version: need {version} but have {_actual}")


# TODO: remove bob_version in 0.2
def bob_required_version(version: str, bob_version: None | str = None) -> None:
    bob_required_package_version("bob-build", version, bob_version)
