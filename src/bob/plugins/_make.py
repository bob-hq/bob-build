from pathlib import Path
from typing import List, Optional, Union

from bob.prelude import *

make_rule = rule(
    "make $makeflags",
    always=True,
    restat=True,
    description="MAKE",
    pool="console",
)


def make(
    *outputs: Union[str, Path],
    dir=Path("."),
    file: Optional[Path] = None,
    flags: Optional[List[str]] = None,
    makeoutputs: Optional[List[str]] = None,
    implicit: Optional[RuleInput] = None,
    order_only: Optional[RuleInput] = None,
):
    if flags is None:
        flags = []

    flags = ["-C", dir] + flags

    if file is not None:
        flags = ["-f", file] + flags

    if makeoutputs is not None:
        flags += makeoutputs

    return make_rule(
        *outputs,
        makeflags=flags,
        implicit=implicit,
        order_only=order_only,
    )


__all__ = ["make"]
