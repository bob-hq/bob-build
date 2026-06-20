from typing import TYPE_CHECKING

from bob.api.scope import DictionaryScope, Scope, ScopeList

if TYPE_CHECKING:
    from bob.api.rule import Rule

NINJA_PROVIDED_VARIABLES = {"in", "out"}
NINJA_SPECIAL_VARIABLES = {
    *NINJA_PROVIDED_VARIABLES,
    "command",
    "depfile",
    "deps",
    "msvc_deps_prefix",
    "descrption",
    "dyndep",
    "generator",
    "in_newline",
    "restat",
    "rspfile",
    "rspfile_content",
}


class Variable:
    def __init__(self, name: str, *rules: "Rule") -> None:
        if name in NINJA_SPECIAL_VARIABLES:
            raise ValueError(f'"{name}" is a special Ninja variable')

        for rule in rules:
            if name not in rule.variable_names:
                raise KeyError(name)

        self.rules = rules
        self.name = name

    def get(self) -> str:
        return self.rules[0].variables[self.name]

    def set(self, value: str) -> Scope:
        return ScopeList(
            [DictionaryScope(rule.variables, {self.name: value}) for rule in self.rules]
        )

    def add(self, value: str) -> Scope:
        value = self.get() + value

        return ScopeList(
            [DictionaryScope(rule.variables, {self.name: value}) for rule in self.rules]
        )
