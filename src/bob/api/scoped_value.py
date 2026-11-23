from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar, overload

from bob.api.rule import OutputType, Rule, RuleInput
from bob.api.scope import AttributeScope, Scope
from bob.api.variable import Variable

T = TypeVar("T")


class ScopedValue(Generic[T]):
    def __init__(self, value: T | None = None) -> None:
        self.value = value

    @overload
    def get(
        self, required: Literal[False] = False, default: None = None
    ) -> T | None: ...

    @overload
    def get(self, required: Literal[False] = False, default: T = ...) -> T: ...

    @overload
    def get(self, required: Literal[True] = True, default: T | None = None) -> T: ...

    def get(self, required: bool = True, default: T | None = None) -> T | None:
        if self.value is None:
            if required:
                raise ValueError("Required non-present value!")

            return default

        return self.value

    def set(self, value: T) -> Scope:
        return AttributeScope(self, {"value": value})

    @overload
    def add(self: "ScopedValue[str]", value: str) -> Scope: ...

    @overload
    def add(self: "ScopedValue[list[T]]", value: list[T]) -> Scope: ...

    def add(self, value: Any) -> Scope:
        return self.set(self.get() + value)


class ScopedRule(ScopedValue[Rule[OutputType]], Generic[OutputType]):
    def __init__(self, base: Rule[OutputType]) -> None:
        super().__init__(base)

        self.single_input = base.single_input
        self.single_output = base.single_output
        self.variable_names = base.variable_names
        self.variables: dict[str, RuleInput.Multiple] = {}

    def set(self, value: Rule[OutputType]) -> Scope:
        if value.single_input != self.single_input:
            raise ValueError(
                "Invalid rule provided: expected a rule which accepts "
                + ("a single input!" if self.single_input else "multiple inputs!")
            )
        if value.single_output != self.single_output:
            raise ValueError(
                "Invalid rule provided: expected a rule which accepts "
                + ("a single output!" if self.single_output else "multiple outputs!")
            )

        return super().set(value)

    def build(
        self,
        *outputs: str | Path,
        inputs: Sequence[RuleInput.Type] | None = None,
        implicit: Sequence[RuleInput.Type] | None = None,
        order_only: Sequence[RuleInput.Type] | None = None,
        implicit_outputs: Sequence[str | Path] | None = None,
        pool: str | None = None,
        dyndep: str | None = None,
        variables: Mapping[str, RuleInput.Multiple] | None = None,
    ) -> OutputType:
        assert self.value is not None

        variables = {
            **{
                key: value
                for key, value in self.variables.items()
                if key in self.value.variable_names
            },
            **(variables or {}),
        }

        return self.value.build(
            *outputs,
            inputs=inputs,
            implicit=implicit,
            order_only=order_only,
            implicit_outputs=implicit_outputs,
            pool=pool,
            dyndep=dyndep,
            variables=variables,
        )

    def __getitem__(self, name: str) -> Variable:
        return Variable(name, self)
