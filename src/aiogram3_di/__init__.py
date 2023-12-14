__all__ = (
    "DIMiddleware",
    "Depends",
    "__version__",
)

from importlib.metadata import version as _version

from .middleware import DIMiddleware
from .depends import Depends

__version__ = _version("aiogram3-di")
