from collections.abc import Callable
from typing import Any


class DIManager:

    __slots__ = "_dependency_overrides"

    def __init__(
            self,
            *,
            dependency_overrides: dict[Callable[..., Any], Callable[..., Any]],
    ) -> None:
        self._dependency_overrides = dependency_overrides

    @property
    def dependency_overrides(self) -> dict[Callable[..., Any], Callable[..., Any]]:
        return self._dependency_overrides

    @dependency_overrides.setter
    def dependency_overrides(self, value: dict[Callable[..., Any], Callable[..., Any]]) -> None:
        self._dependency_overrides = value
