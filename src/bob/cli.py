import os
import subprocess
from pathlib import Path
from typing import Sequence

import rich_click as click

from bob.constants import (
    BOB_BUILDDIR_SUBDIRECTORY,
    DEFAULT_BUILDDIR,
    get_build_ninja_path,
    get_used_configs_path,
)
from bob.utilities.click import SeparateUnprocessedArgumentsCommand


def complete_targets(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> list[str]:
    builddir: Path = ctx.params.get("builddir", DEFAULT_BUILDDIR)

    p = subprocess.run(
        [
            "ninja",
            "-f",
            get_build_ninja_path(builddir),
            "-t",
            "targets",
            "all",
        ],
        capture_output=True,
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
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> list[str]:
    builddir: Path = ctx.params.get("builddir", DEFAULT_BUILDDIR)

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
@click.option(
    "-B",
    "--builddir",
    help="The directory to put the Bob outputs in.",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_BUILDDIR,
    show_default=True,
)
@click.option(
    "--bobfile",
    "-f",
    "bobfile",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="The input Bobfile.",
    default=Path("Bobfile"),
    show_default=True,
)
@click.option(
    "-c",
    "--config",
    "configs",
    multiple=True,
    help="Supply the given config option.",
    shell_complete=complete_configs,
)
@click.option(
    "--use-current-configs",
    is_flag=True,
    help="Use the current configs saved from previously configuring.",
)
@click.option(
    "--allow-build-outside-builddir",
    is_flag=True,
    help="Allow building targets outside of the build directory.",
)
def configure(
    builddir: Path,
    bobfile: Path,
    configs: Sequence[str],
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
@click.option(
    "-B",
    "--builddir",
    help="The directory to put the Bob outputs in.",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_BUILDDIR,
    show_default=True,
)
@click.option(
    "--bobfile",
    "-f",
    "bobfile",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="The input Bobfile.",
    default=Path("Bobfile"),
    show_default=True,
)
@click.option(
    "-c",
    "--config",
    "configs",
    multiple=True,
    help="Supply the given config option.",
    shell_complete=complete_configs,
)
@click.option(
    "-u",
    "--use-current-configs",
    is_flag=True,
    help="Use the current configs saved from previously configuring.",
)
@click.option("--clean", "do_clean", is_flag=True, help="Clean before building.")
@click.option(
    "--no-compdb", is_flag=True, help="Don't create a compilation DB for this build."
)
@click.option(
    "--symlink-compdb",
    is_flag=True,
    help="Create a symlink to the compilation DB in the current directory.",
)
@click.option(
    "-j",
    "--jobs",
    "jobs",
    type=int,
    default=os.cpu_count(),
    help="Run this many jobs in parallel (0 means infinity).",
    show_default=True,
)
@click.option(
    "--no-jobserver",
    is_flag=True,
    help="Don't provide a jobserver.",
)
@click.option(
    "--no-pretty",
    is_flag=True,
    envvar="BOB_NO_PRETTY",
    help="Print the raw Ninja output rather than pretty printing the build process.",
    show_envvar=True,
)
@click.option(
    "--allow-build-outside-builddir",
    is_flag=True,
    help="Allow building targets outside of the build directory.",
)
@click.argument("targets", shell_complete=complete_targets, nargs=-1)
@click.pass_context
def build(
    ctx: click.Context,
    builddir: Path,
    bobfile: Path,
    do_clean: bool,
    no_compdb: bool,
    symlink_compdb: bool,
    configs: Sequence[str],
    use_current_configs: bool,
    targets: Sequence[str],
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
        extra_ninja_arguments=ctx.meta["unprocessed"],
    )


@cli.command
@click.option(
    "-B",
    "--builddir",
    help="The directory to put the Bob outputs in.",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_BUILDDIR,
    show_default=True,
)
@click.option(
    "--force",
    help="Remove the build directory even if it doesn't match a Bob build directory.",
    is_flag=True,
)
def clean(builddir: Path, force: bool) -> None:
    """Clean all built files."""

    from bob.commands.clean import clean

    clean(builddir=builddir, force=force)


@cli.command
@click.option(
    "-B",
    "--builddir",
    help="The directory to put the Bob outputs in.",
    type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_BUILDDIR,
    show_default=True,
)
@click.option(
    "--bobfile",
    "-f",
    "bobfile",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="The input Bobfile.",
    default=Path("Bobfile"),
    show_default=True,
)
@click.option(
    "--dont-symlink",
    help="Don't create a symlink in the current directory.",
    is_flag=True,
)
@click.option(
    "-c",
    "--config",
    "configs",
    multiple=True,
    help="Supply the given config option.",
    shell_complete=complete_configs,
)
@click.option(
    "--use-current-configs",
    is_flag=True,
    help="Use the current configs saved from previously configuring.",
)
def compdb(
    builddir: Path,
    bobfile: Path,
    dont_symlink: bool,
    configs: Sequence[str],
    use_current_configs: bool,
) -> None:
    """Create a compilation database for the project."""

    from bob.commands.compdb import compdb

    compdb(
        builddir=builddir,
        bobfile=bobfile,
        dont_symlink=dont_symlink,
        configs=configs,
        use_current_configs=use_current_configs,
    )


@cli.command
@click.option(
    "--shell",
    help="The shell to install completions for.",
    default=Path(os.environ["SHELL"]).name if "SHELL" in os.environ else None,
    show_default=True,
)
def completions(shell: str) -> None:
    """Install shell completions for Bob."""

    from bob.commands.completions import completions

    completions(shell=shell)
