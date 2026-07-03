import rich_click as click


class SeparateUnprocessedArgumentsCommand(click.Command):
    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if "--" in args:
            index = args.index("--")
            ctx.meta["unprocessed"] = args[index + 1 :]
            args = args[:index]
        else:
            ctx.meta["unprocessed"] = []

        return super().parse_args(ctx, args)
