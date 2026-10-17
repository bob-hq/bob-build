from collections.abc import Callable
from typing import TypeVar

import click as _click
import rich_click as click
from typing_extensions import override

FC = TypeVar("FC", bound=Callable[..., object] | _click.Command)


def option(*param_decls: str, **attrs: object) -> Callable[[FC], FC]:
    return _click.option(*param_decls, cls=click.RichOption, **attrs)


def argument(*param_decls: str, **attrs: object) -> Callable[[FC], FC]:
    return _click.argument(*param_decls, cls=click.RichArgument, **attrs)


class SeparateUnprocessedArgumentsCommand(click.Command):
    @override
    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if "--" in args:
            index = args.index("--")
            ctx.meta["unprocessed"] = args[index + 1 :]
            args = args[:index]
        else:
            ctx.meta["unprocessed"] = []

        return super().parse_args(ctx, args)
