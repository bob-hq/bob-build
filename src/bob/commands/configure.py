import json
from collections.abc import Collection
from pathlib import Path
from typing import cast

from bob.constants import get_build_ninja_path, get_configs_path
from bob.core.context import Context


def configure(
    builddir: Path,
    bobfile: Path,
    configs: Collection[str] = (),
    use_current_configs: bool = False,
    lazy: bool = False,
    allow_build_outside_builddir: bool = False,
) -> None:
    configs_path = get_configs_path(builddir)

    resolved_configs: dict[str, str] = {}
    if use_current_configs:
        if len(configs) != 0:
            raise ValueError("Can't provide configs and use current configs!")
        if not configs_path.is_file():
            raise FileNotFoundError(
                f"Can't use the current configs: {builddir} hasn't been configured yet"
            )
        with open(configs_path, "r") as f:
            resolved_configs = cast(dict[str, str], json.load(f))
    else:
        for config in configs:
            key, separator, value = config.partition("=")
            if not separator or not key:
                raise ValueError(f'Invalid config "{config}", expected KEY=VALUE')
            resolved_configs[key] = value

        serialized_configs = json.dumps(resolved_configs, indent=4, sort_keys=True)
        if not (
            configs_path.exists() and configs_path.read_text() == serialized_configs
        ):
            configs_path.parent.mkdir(parents=True, exist_ok=True)
            configs_path.write_text(serialized_configs)

    if lazy and get_build_ninja_path(builddir).exists():
        return

    with Context(
        builddir, bobfile, resolved_configs, allow_build_outside_builddir
    ) as context:
        context.evaluate(bobfile, restore_configs=False)
