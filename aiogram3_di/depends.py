from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any


@dataclass(slots=True)
class Depends:
    func: Callable[..., Any] | None = None
    use_cache: bool = field(default=True, kw_only=True)
