from collections.abc import Callable
from typing import Any


class Depends:

    __slots__ = ('func', 'use_cache')

    def __init__(self, func: Callable[..., Any] | None = None, *, use_cache: bool = True) -> None:
        self.func = func
        self.use_cache = use_cache
