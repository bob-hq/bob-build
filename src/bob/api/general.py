import re
from importlib.metadata import version as importlib_version
from logging import getLogger
from typing import Literal, overload

from bob.core.context import Context


@overload
def config(name: str, required: Literal[False], default: str) -> str: ...


@overload
def config(name: str, *, default: str) -> str: ...


@overload
def config(
    name: str, required: Literal[False] = False, default: str | None = None
) -> str | None: ...


@overload
def config(name: str, required: Literal[True]) -> str: ...


def config(name: str, required: bool = False, default: str | None = None) -> str | None:
    context = Context.current()

    context.used_configs.add(name)

    if name not in context.configs:
        if required:
            raise KeyError(
                f'Missing required config "{name}", pass it with `-c {name}=...`'
            )

        getLogger(__name__).info(f'Unset config "{name}"')
        return default

    return context.configs[name]


def _release_numbers(version: str) -> tuple[int, int, int, bool]:
    """Parse the major, minor and patch numbers of e.g. "1.2", "0.1.12" or "0.2.0.dev1".

    Also returns whether the version is a pre-release (e.g. "0.2.0.dev1" or "0.2.0rc1"), which comes
    before the release it names.
    """

    match = re.match(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", version)
    if match is None:
        raise ValueError(f'Failed to parse version "{version}"')

    major, minor, patch = (int(number or 0) for number in match.groups())

    # Following PEP 440, ignoring the local part ("+..."). A pre-release tag comes right after the
    # release numbers, so e.g. "0.1.12.post1.dev1" (a pre-release of a post-release) isn't one.
    suffix = version[match.end() :].partition("+")[0].lower()
    prerelease = (
        re.match(r"[-_.]?(dev|a|alpha|b|beta|c|rc|pre|preview)", suffix) is not None
    )

    return major, minor, patch, prerelease


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
    actual_major, actual_minor, actual_patch, actual_prerelease = _release_numbers(
        _actual
    )

    if required_major == 0:
        assert len(required_rest) == 1, (
            f'For major 0 you must specify patch version as well, e.g. "0.{required_minor}.X", got: "{version}"'
        )
    else:
        assert len(required_rest) == 0, (
            f'For non-zero major {required_major} you must not specify patch version, e.g. "{required_major}.{required_minor}", got: "{version}"'
        )

    required_patch = required_rest[0] if required_major == 0 else 0
    if (
        required_major != actual_major
        or actual_minor < required_minor
        or (
            required_major == 0
            and (actual_minor != required_minor or actual_patch < required_patch)
        )
        # A pre-release of exactly the required version lacks some of its features.
        or (
            actual_prerelease
            and (actual_minor, actual_patch) == (required_minor, required_patch)
        )
    ):
        raise ValueError(
            f"Invalid {package} version: need {version} but have {_actual}"
        )


# TODO: remove bob_version in 0.2
def bob_required_version(version: str, bob_version: None | str = None) -> None:
    bob_required_package_version("bob-build", version, bob_version)
