import shutil
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Union

from bob.prelude import *

cc = rule(
    "$ccbin -MMD -MT $out -MF $out.d $cflags -c $in -o $out",
    description="CC",
    depfile="$out.d",
    deps="gcc",
    compile_command="$ccbin -MMD -MT $out -MF $out.d $cflags -c $in -o $out",
)
cc_provider = RuleProvider(cc)
asm = rule(
    "$asbin -MMD -MT $out -MF $out.d $asflags -c $in -o $out",
    description="AS",
    depfile="$out.d",
    deps="gcc",
    compile_command="$asbin -MMD -MT $out -MF $out.d $asflags -c $in -o $out",
)
asm_provider = RuleProvider(asm)
ld = rule(
    "$ldbin $cflags $ldflags -o $out $in $ldlibs",
    description="LD",
)
ld_provider = RuleProvider(ld)
ar = rule(
    "rm -f $out && $arbin crs $out $in",
    description="AR",
)
ar_provider = RuleProvider(ar)

ccbinvar = cc["ccbin"]
asbinvar = asm["asbin"]
ldbinvar = ld["ldbin"]
arbinvar = ar["arbin"]

cflags = variable("cflags", cc, ld)
asflags = asm["asflags"]
ldflags = ld["ldflags"]

cflags.provide(["-fdiagnostics-color=always"])
asflags.provide([])
ldflags.provide([])


@dataclass
class Bundle:
    """A bundle that can be used to create dependent binaries and libraries."""

    objects: List[Union[str, Path, RootRelativePath, FileTarget]] = field(
        default_factory=list
    )
    ldlibs: List[Union[str, Path, RootRelativePath, FileTarget]] = field(
        default_factory=list
    )
    order_only: Optional[RuleInput] = None
    cflags: List[str] = field(default_factory=list)
    asflags: List[str] = field(default_factory=list)
    ldflags: List[str] = field(default_factory=list)

    def __add__(self, other: "Bundle"):
        return Bundle(
            objects=self.objects + other.objects,
            order_only=rule_input_add(self.order_only, other.order_only),
            ldlibs=self.ldlibs + other.ldlibs,
            cflags=self.cflags + other.cflags,
            asflags=self.asflags + other.asflags,
            ldflags=self.ldflags + other.ldflags,
        )

    @contextmanager
    def scope(self):
        with (
            cflags.extend(self.cflags),
            asflags.extend(self.asflags),
            ldflags.extend(self.ldflags),
        ):
            yield self.objects, self.ldlibs, self.order_only


default_bundles = Provider[List[Bundle]]([])
"""The default bundles to use for C targets."""

objects = []
"""All built C objects."""


def object(
    source: SingleRuleInput,
    bundles: Optional[List[Bundle]] = None,
    implicit: Optional[RuleInput] = None,
    order_only: Optional[RuleInput] = None,
    implicit_outputs: Optional[RuleInput] = None,
    name_transform: Callable[[Path], Union[str, Path]] = lambda s: s,
):
    """Build a C object created from the given C or Assembly source file."""

    source = rule_input_resolve(source, path_only=True, single=True)

    name = name_transform(source.with_suffix(".o").value)

    with sum((bundles or []) + default_bundles.get(), Bundle()).scope() as (
        bundle_objects,
        bundle_ldlibs,
        bundle_order_only,
    ):
        if source.suffix == ".c":
            cc = cc_provider.get()
            result = cc(
                name,
                inputs=[source],
                implicit=implicit,
                order_only=rule_input_add(order_only, bundle_order_only),
                implicit_outputs=implicit_outputs,
            )
        elif source.suffix == ".S" or source.suffix == ".s":
            asm = asm_provider.get()
            result = asm(
                name,
                inputs=[source],
                implicit=implicit,
                order_only=rule_input_add(order_only, bundle_order_only),
                implicit_outputs=implicit_outputs,
            )
        else:
            raise ValueError(f"Unknown C source extension for file: {source}")

    objects.append(result)
    return result


@contextmanager
def _expand(
    name: str,
    sources: List[Union[str, Path, RootRelativePath, FileTarget]],
    inputs: Optional[RuleInput] = None,
    bundles: Optional[List[Bundle]] = None,
    implicit: Optional[RuleInput] = None,
    order_only: Optional[RuleInput] = None,
):
    if inputs is None:
        inputs = []

    if not isinstance(inputs, list):
        inputs = [inputs]

    total_bundles = sum(bundles or [], Bundle())

    yield (
        (
            [
                object(
                    source,
                    implicit=implicit,
                    order_only=order_only,
                    bundles=bundles,
                    name_transform=lambda p: Path("obj") / name / p,
                )
                for source in sources
            ]
            + (inputs or [])
            + total_bundles.objects
        ),
        total_bundles.ldlibs,
    )
    return


def binary(
    name: str,
    sources: List[Union[str, Path, RootRelativePath, FileTarget]],
    inputs: Optional[RuleInput] = None,
    bundles: Optional[List[Bundle]] = None,
    implicit: Optional[RuleInput] = None,
    order_only: Optional[RuleInput] = None,
    implicit_outputs: Optional[RuleInput] = None,
    ldlibs: Optional[List[str]] = None,
):
    """Build a binary from the given C sources and additional inputs."""

    if ldlibs is None:
        ldlibs = []

    ld = ld_provider.get()

    with (
        _expand(
            name=name,
            sources=sources,
            inputs=inputs,
            bundles=bundles,
            implicit=implicit,
            order_only=order_only,
        ) as (inputs, bundle_ldlibs),
        ld["ldlibs"].provide(ldlibs + bundle_ldlibs),
    ):
        return ld(
            name,
            inputs=inputs,
            implicit=bundle_ldlibs,
            implicit_outputs=implicit_outputs,
        )


def static_library(
    name: str,
    sources: List[Union[str, Path, RootRelativePath, FileTarget]],
    inputs: Optional[RuleInput] = None,
    bundles: Optional[List[Bundle]] = None,
    implicit: Optional[RuleInput] = None,
    order_only: Optional[RuleInput] = None,
    implicit_outputs: Optional[RuleInput] = None,
):
    """Build a static archive from the given C sources and additional inputs."""

    ar = ar_provider.get()

    with _expand(
        name=name,
        sources=sources,
        inputs=inputs,
        bundles=bundles,
        implicit=implicit,
        order_only=order_only,
    ) as (inputs, bundle_ldlibs):
        return ar(name + ".a", inputs=inputs, implicit_outputs=implicit_outputs)


def static_library_bundle(
    name: str,
    sources: List[Union[str, Path, RootRelativePath, FileTarget]],
    inputs: Optional[List[str]] = None,
    bundles: Optional[List[Bundle]] = None,
    public_cflags: Optional[List[str]] = None,
    public_asflags: Optional[List[str]] = None,
    public_ldflags: Optional[List[str]] = None,
    implicit: Optional[RuleInput] = None,
    order_only: Optional[RuleInput] = None,
    implicit_outputs: Optional[RuleInput] = None,
):
    """Build a static archive from the given C sources and additional inputs and return a bundle which lets other binaries and libraries use this library."""

    if public_cflags is None:
        public_cflags = []
    if public_asflags is None:
        public_asflags = []
    if public_ldflags is None:
        public_ldflags = []

    with (
        cflags.extend(public_cflags),
        asflags.extend(public_asflags),
        ldflags.extend(public_ldflags),
    ):
        library = static_library(
            name=name,
            sources=sources,
            inputs=inputs,
            bundles=bundles,
            implicit=implicit,
            order_only=order_only,
            implicit_outputs=implicit_outputs,
        )

    ldlibs = [library]
    for bundle in (bundles or []) + default_bundles.get():
        ldlibs += bundle.ldlibs

    return Bundle(
        ldlibs=ldlibs,
        cflags=public_cflags,
        asflags=public_asflags,
        ldflags=public_ldflags,
    )


def toolchain(
    ccbin: Union[str, List[str]],
    arbin: Union[str, List[str]],
    asbin: Optional[Union[str, List[str]]] = None,
    ldbin: Optional[Union[str, List[str]]] = None,
):
    """
    Use the given C toolchain.
    The `ccbin` is used for `asbin` and `ldbin` if they aren't provided.
    """

    if asbin is None:
        asbin = ccbin

    if ldbin is None:
        ldbin = ccbin

    if isinstance(ccbin, list) and len(ccbin) == 1:
        ccbin = ccbin[0]

    if isinstance(asbin, list) and len(asbin) == 1:
        asbin = asbin[0]

    if isinstance(ldbin, list) and len(ldbin) == 1:
        ldbin = ldbin[0]

    if isinstance(arbin, list) and len(arbin) == 1:
        arbin = arbin[0]

    if isinstance(ccbin, str) and not Path(ccbin).exists():
        ccbin = shutil.which(ccbin)

    if isinstance(asbin, str) and not Path(asbin).exists():
        asbin = shutil.which(asbin)

    if isinstance(ldbin, str) and not Path(ldbin).exists():
        ldbin = shutil.which(ldbin)

    if isinstance(arbin, str) and not Path(arbin).exists():
        arbin = shutil.which(arbin)

    return (
        ccbinvar.provide(ccbin)
        | asbinvar.provide(asbin)
        | ldbinvar.provide(ldbin)
        | arbinvar.provide(arbin)
    )


def add_include_path(path: RuleInput):
    return cflags.extend([f"-I{p}" for p in rule_input_resolve(path, path_only=True)])


__all__ = [
    "cc",
    "asm",
    "ld",
    "ar",
    "ccbinvar",
    "asbinvar",
    "ldbinvar",
    "arbinvar",
    "cc_provider",
    "asm_provider",
    "ld_provider",
    "ar_provider",
    "cflags",
    "asflags",
    "ldflags",
    "Bundle",
    "object",
    "objects",
    "binary",
    "static_library",
    "static_library_bundle",
    "toolchain",
    "add_include_path",
]
