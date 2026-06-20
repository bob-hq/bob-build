from typing import TYPE_CHECKING

from ninja.ninja_syntax import escape as ninja_escape

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

    def provide(self, value: str) -> Scope:
        resolved_value = ninja_escape(value)

        return ScopeList(
            [
                DictionaryScope(rule.variables, {self.name: resolved_value})
                for rule in self.rules
            ]
        )
