import abc
from typing import Any, Self


class Scope(abc.ABC):
    @abc.abstractmethod
    def close(self) -> None: ...

    def __enter__(self) -> "Scope":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __or__(self, other: Self | "ScopeList") -> "Scope":
        return ScopeList([self]) | other


class ScopeList(Scope):
    def __init__(self, scopes: list[Scope]) -> None:
        self.scopes = scopes

    def close(self) -> None:
        for scope in self.scopes:
            scope.close()

    def __or__(self, other: Scope | Self) -> Scope:
        if isinstance(other, ScopeList):
            return ScopeList(self.scopes + other.scopes)
        return ScopeList(self.scopes + [other])


class DictionaryScope(Scope):
    def __init__(self, variables: dict[str, Any], changes: dict[str, Any]) -> None:
        self.variables = variables
        self.changes = changes

        original: dict[str, Any] = {}
        for key, value in changes.items():
            if key in variables:
                original[key] = variables.pop(key)

            variables[key] = value

        self.original = original

    def close(self) -> None:
        for key in self.changes:
            assert self.variables[key] == self.changes[key]

            if key in self.original:
                self.variables[key] = self.original[key]
            else:
                self.variables.pop(key)

        self.original = {}
        self.changes = {}
        self.variables = {}
