from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar, overload

from bob.api.rule import OutputType, Rule, RuleInput
from bob.api.scope import AttributeScope, Scope
from bob.api.variable import Variable

T = TypeVar("T")


class ScopedValue(Generic[T]):
    def __init__(self, value: None | T = None) -> None:
        self.value = value

    # `default` is only meaningful when the value isn't required.
    @overload
    def get(self, required: Literal[True] = True) -> T: ...

    @overload
    def get(self, required: Literal[False]) -> None | T: ...

    @overload
    def get(self, required: Literal[False], default: T) -> T: ...

    def get(self, required: bool = True, default: None | T = None) -> None | T:
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
                "Invalid rule provided: expected a rule which accepts a single input!"
                if self.single_input
                else "Invalid rule provided: expected a rule which accepts multiple inputs!"
            )
        if value.single_output != self.single_output:
            raise ValueError(
                "Invalid rule provided: expected a rule which produces a single output!"
            )

        return super().set(value)

    def build(
        self,
        *outputs: str | Path,
        inputs: None | Sequence[RuleInput.Type] = None,
        implicit: None | Sequence[RuleInput.Type] = None,
        order_only: None | Sequence[RuleInput.Type] = None,
        implicit_outputs: None | Sequence[str | Path] = None,
        pool: None | str = None,
        dyndep: None | str = None,
        variables: None | Mapping[str, RuleInput.Multiple] = None,
    ) -> OutputType:
        rule = self.get()

        # Variables passed explicitly to `build` take precedence over the scoped ones.
        merged_variables = {
            key: value
            for key, value in self.variables.items()
            if key in rule.variable_names
        } | dict(variables or {})

        return rule.build(
            *outputs,
            inputs=inputs,
            implicit=implicit,
            order_only=order_only,
            implicit_outputs=implicit_outputs,
            pool=pool,
            dyndep=dyndep,
            variables=merged_variables,
        )

    def __getitem__(self, name: str) -> Variable:
        return Variable(name, self)
