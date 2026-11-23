import abc
from types import TracebackType
from typing import Any

from typing_extensions import Self

from bob.core.context import Context


class Scope(abc.ABC):
    def __init__(self) -> None:
        self._closed = False
        self._context: Context | None = None
        self._track()

    def _track(self) -> None:
        context = Context.current()
        if context.track_scopes:
            context.scopes.append(self)
            self._context = context

    @abc.abstractmethod
    def _close(self) -> None: ...

    def __enter__(self) -> "Self":
        return self

    def close(self) -> None:
        if self._closed:
            return

        self._close()
        self._closed = True

        if self._context is not None:
            self._context.scopes.remove(self)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def __or__(self, other: "Scope | ScopeStack") -> "Scope":
        return ScopeStack([self]) | other


class ScopeStack(Scope):
    def __init__(self, scopes: list[Scope]) -> None:
        super().__init__()
        self.scopes = scopes

    def _track(self) -> None:
        # Stacks are not tracked by themselves, only their children are.
        # This is required since temporary stack objects (which are created e.g. in or expressions) aren't closed,
        # so tracking them would leak them.
        pass

    def _close(self) -> None:
        for scope in reversed(self.scopes):
            scope.close()

    def __or__(self, other: "Scope | ScopeStack") -> Scope:
        if isinstance(other, ScopeStack):
            return ScopeStack(self.scopes + other.scopes)
        return ScopeStack(self.scopes + [other])


# TODO: remove in 0.2
ScopeList = ScopeStack


class DictionaryScope(Scope):
    def __init__(self, variables: dict[str, Any], changes: dict[str, Any]) -> None:
        super().__init__()
        self.variables = variables
        self.changes = changes

        original: dict[str, Any] = {}
        for key, value in changes.items():
            if key in variables:
                original[key] = variables.pop(key)

            variables[key] = value

        self.original = original

    def _close(self) -> None:
        for key in self.changes:
            assert self.variables[key] == self.changes[key], (
                f"Expected {key} to be {self.changes[key]} when closing the scope but got: {self.variables[key]}"
            )

            if key in self.original:
                self.variables[key] = self.original[key]
            else:
                self.variables.pop(key)

        self.original = {}
        self.changes = {}
        self.variables = {}


class AttributeScope(Scope):
    def __init__(self, object: Any, changes: dict[str, Any]) -> None:
        super().__init__()
        self.object = object
        self.changes = changes

        original: dict[str, Any] = {}
        for key, value in changes.items():
            if hasattr(object, key):
                original[key] = getattr(object, key)

            setattr(object, key, value)

        self.original = original

    def _close(self) -> None:
        for key in self.changes:
            # The `object` mustn't have changed underneath our feet, we have no sensible action in that case.
            assert getattr(self.object, key) == self.changes[key], (
                f"Expected {key} to be {self.changes[key]} when closing the scope but got: {getattr(self.object, key)}"
            )

            if key in self.original:
                setattr(self.object, key, self.original[key])
            else:
                delattr(self.object, key)

        self.original = {}
        self.changes = {}
        self.object = None


def plugin_scope() -> Scope:
    context = Context.current()
    return AttributeScope(context, {"track_scopes": False})
