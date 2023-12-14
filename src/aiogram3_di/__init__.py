__all__ = (
    "Depends",
    "DIManager",
    "setup_di",
    "__version__",
)

from importlib.metadata import version as _version

from .depends import Depends
from .manager import DIManager
from .setup import setup_di

__version__ = _version("aiogram3-di")
