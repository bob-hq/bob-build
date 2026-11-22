from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, overload

from bob.api.scope import DictionaryScope, Scope, ScopeStack

if TYPE_CHECKING:
    from bob.api.rule import Rule, RuleInput
    from bob.api.scoped_value import ScopedRule

NINJA_PROVIDED_VARIABLES = {"in", "out"}
NINJA_SPECIAL_VARIABLES = {
    *NINJA_PROVIDED_VARIABLES,
    "command",
    "depfile",
    "deps",
    "msvc_deps_prefix",
    "description",
    "dyndep",
    "generator",
    "in_newline",
    "pool",
    "restat",
    "rspfile",
    "rspfile_content",
}


class Variable:
    def __init__(self, name: str, *rules: "Rule[Any] | ScopedRule[Any]") -> None:
        if name in NINJA_SPECIAL_VARIABLES:
            raise ValueError(f'"{name}" is a special Ninja variable')

        for rule in rules:
            if name not in rule.variable_names:
                raise KeyError(name)

        self.rules: tuple[Rule[Any] | ScopedRule[Any], ...] = rules
        self.name: str = name

    def get(self) -> "RuleInput.Multiple":
        return self.rules[0].variables[self.name]

    def set(self, value: "RuleInput.Multiple") -> Scope:
        return ScopeStack(
            [DictionaryScope(rule.variables, {self.name: value}) for rule in self.rules]
        )

    @overload
    def add(self, value: str) -> Scope: ...

    @overload
    def add(self, value: "Sequence[RuleInput.Type]") -> Scope: ...

    def add(self, value: "str | Sequence[RuleInput.Type]") -> Scope:
        current = self.get()

        combined: RuleInput.Multiple
        if isinstance(current, str) and isinstance(value, str):
            combined = current + value
        elif (
            isinstance(current, Sequence)
            and not isinstance(current, str)
            and not isinstance(value, str)
            # Not redundant: untyped callers can pass anything, e.g. a single `Path`.
            and isinstance(value, Sequence)  # pyright: ignore[reportUnnecessaryIsInstance]
        ):
            combined = [*current, *value]
        else:
            raise TypeError(
                f'Cannot add {value!r} to variable "{self.name}" whose value is {current!r}'
            )

        return self.set(combined)
