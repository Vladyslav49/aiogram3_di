from collections.abc import Callable
from typing import Any, Optional


class Depends:

    __slots__ = ('func', 'use_cache')

    def __init__(self, func: Optional[Callable[..., Any]] = None, *, use_cache: bool = True) -> None:
        self.func = func
        self.use_cache = use_cache
