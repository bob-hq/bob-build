import os
import subprocess
from collections.abc import Collection
from pathlib import Path
from typing import cast

import rich_click as click
from ninja import BIN_DIR as NINJA_BIN_DIR

from bob.constants import (
    BOB_BUILDDIR_SUBDIRECTORY,
    DEFAULT_BUILDDIR,
    get_build_ninja_path,
    get_used_configs_path,
)
from bob.utilities.click import SeparateUnprocessedArgumentsCommand, argument, option


def complete_targets(
    ctx: click.Context, _param: click.Parameter, incomplete: str
) -> list[str]:
    builddir = cast(Path, ctx.params.get("builddir", DEFAULT_BUILDDIR))

    p = subprocess.run(
        [
            Path(NINJA_BIN_DIR) / "ninja",
            "-f",
            get_build_ninja_path(builddir),
            "-t",
            "targets",
            "all",
        ],
        capture_output=True,
        check=False,
    )

    if p.returncode != 0:
        return []

    return [
        line.partition(b":")[0].decode()
        for line in p.stdout.splitlines()
        if line.startswith(incomplete.encode())
        and f"/{BOB_BUILDDIR_SUBDIRECTORY}/".encode() not in line
    ]


def complete_configs(
    ctx: click.Context, _param: click.Parameter, incomplete: str
) -> list[str]:
    builddir = cast(Path, ctx.params.get("builddir", DEFAULT_BUILDDIR))

    used_configs_path = get_used_configs_path(builddir)

    if not used_configs_path.is_file():
        return []

    return [
        f"{config}="
        for config in used_configs_path.read_text().splitlines()
        if incomplete in config
    ]


@click.group
def cli() -> None:
    """The ergonomic Ninja-based build system."""
    from bob.log import setup

    setup()


@cli.command()
@option(
    "-B",
    "--builddir",
    help="The directory to put the Bob outputs in.",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_BUILDDIR,
    show_default=True,
)
@option(
    "--bobfile",
    "-f",
    "bobfile",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="The input Bobfile.",
    default=Path("Bobfile"),
    show_default=True,
)
@option(
    "-c",
    "--config",
    "configs",
    multiple=True,
    help="Supply the given config option.",
    shell_complete=complete_configs,
)
@option(
    "--use-current-configs",
    is_flag=True,
    help="Use the current configs saved from previously configuring.",
)
@option(
    "--allow-build-outside-builddir",
    is_flag=True,
    help="Allow building targets outside of the build directory.",
)
def configure(
    builddir: Path,
    bobfile: Path,
    configs: Collection[str],
    use_current_configs: bool,
    allow_build_outside_builddir: bool,
) -> None:
    """Generate the Ninja file to build the project."""

    from bob.commands.configure import configure

    configure(
        builddir=builddir,
        bobfile=bobfile,
        configs=configs,
        use_current_configs=use_current_configs,
        allow_build_outside_builddir=allow_build_outside_builddir,
    )


@cli.command(cls=SeparateUnprocessedArgumentsCommand)
@option(
    "-B",
    "--builddir",
    help="The directory to put the Bob outputs in.",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_BUILDDIR,
    show_default=True,
)
@option(
    "--bobfile",
    "-f",
    "bobfile",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="The input Bobfile.",
    default=Path("Bobfile"),
    show_default=True,
)
@option(
    "-c",
    "--config",
    "configs",
    multiple=True,
    help="Supply the given config option.",
    shell_complete=complete_configs,
)
@option(
    "-u",
    "--use-current-configs",
    is_flag=True,
    help="Use the current configs saved from previously configuring.",
)
@option("--clean", "do_clean", is_flag=True, help="Clean before building.")
@option(
    "--no-compdb", is_flag=True, help="Don't create a compilation DB for this build."
)
@option(
    "--symlink-compdb",
    is_flag=True,
    help="Create a symlink to the compilation DB in the current directory.",
)
@option(
    "-j",
    "--jobs",
    "jobs",
    type=int,
    default=os.cpu_count(),
    help="Run this many jobs in parallel (0 means infinity).",
    show_default=True,
)
@option(
    "--no-jobserver",
    is_flag=True,
    help="Don't provide a jobserver.",
)
@option(
    "--no-pretty",
    is_flag=True,
    envvar="BOB_NO_PRETTY",
    help="Print the raw Ninja output rather than pretty printing the build process.",
    show_envvar=True,
)
@option(
    "--allow-build-outside-builddir",
    is_flag=True,
    help="Allow building targets outside of the build directory.",
)
@argument("targets", shell_complete=complete_targets, nargs=-1)
@click.pass_context
def build(
    ctx: click.Context,
    builddir: Path,
    bobfile: Path,
    do_clean: bool,
    no_compdb: bool,
    symlink_compdb: bool,
    configs: Collection[str],
    use_current_configs: bool,
    targets: Collection[str],
    jobs: None | int,
    no_jobserver: bool,
    no_pretty: bool,
    allow_build_outside_builddir: bool,
) -> None:
    """Build the given Bob project."""

    from bob.commands.build import build

    build(
        builddir=builddir,
        bobfile=bobfile,
        do_clean=do_clean,
        no_compdb=no_compdb,
        symlink_compdb=symlink_compdb,
        configs=configs,
        use_current_configs=use_current_configs,
        targets=targets,
        jobs=jobs,
        no_jobserver=no_jobserver,
        no_pretty=no_pretty,
        allow_build_outside_builddir=allow_build_outside_builddir,
        extra_ninja_arguments=cast(list[str], ctx.meta["unprocessed"]),
    )


@cli.command
@option(
    "-B",
    "--builddir",
    help="The directory to put the Bob outputs in.",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_BUILDDIR,
    show_default=True,
)
@option(
    "--force",
    help="Remove the build directory even if it doesn't match a Bob build directory.",
    is_flag=True,
)
def clean(builddir: Path, force: bool) -> None:
    """Clean all built files."""

    from bob.commands.clean import clean

    clean(builddir=builddir, force=force)


@cli.command
@option(
    "-B",
    "--builddir",
    help="The directory to put the Bob outputs in.",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_BUILDDIR,
    show_default=True,
)
@option(
    "--bobfile",
    "-f",
    "bobfile",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="The input Bobfile.",
    default=Path("Bobfile"),
    show_default=True,
)
@option(
    "--dont-symlink",
    help="Don't create a symlink in the current directory.",
    is_flag=True,
)
@option(
    "-c",
    "--config",
    "configs",
    multiple=True,
    help="Supply the given config option.",
    shell_complete=complete_configs,
)
@option(
    "--use-current-configs",
    is_flag=True,
    help="Use the current configs saved from previously configuring.",
)
@argument("targets", shell_complete=complete_targets, nargs=-1)
def compdb(
    builddir: Path,
    bobfile: Path,
    dont_symlink: bool,
    configs: Collection[str],
    use_current_configs: bool,
    targets: Collection[str],
) -> None:
    """Create a compilation database for the project."""

    from bob.commands.compdb import compdb

    _ = compdb(
        builddir=builddir,
        bobfile=bobfile,
        dont_symlink=dont_symlink,
        configs=configs,
        use_current_configs=use_current_configs,
        targets=targets,
    )


@cli.command
@option(
    "--shell",
    help="The shell to install completions for.",
    default=Path(os.environ["SHELL"]).name if "SHELL" in os.environ else None,
    show_default=True,
)
def completions(shell: str) -> None:
    """Install shell completions for Bob."""

    from bob.commands.completions import completions

    completions(shell=shell)
