from collections.abc import Callable
from typing import Any

from aiogram import Dispatcher
from aiogram.dispatcher.event.telegram import TelegramEventObserver

from aiogram3_di.manager import DIManager
from aiogram3_di.middleware import DIMiddleware


def setup_di(
    dispatcher: Dispatcher,
    *,
    allowed_updates: list[str] | None = None,
    dependency_overrides: dict[Callable[..., Any], Callable[..., Any]] | None = None,
) -> DIManager:
    if not isinstance(dispatcher, Dispatcher):
        raise TypeError("dispatcher must be an instance of aiogram.Dispatcher")

    if allowed_updates is not None:
        for allowed_update in allowed_updates:
            if allowed_update not in dispatcher.observers:
                raise ValueError(f"`{allowed_update}` is not a valid allowed update")

    for allowed_update in allowed_updates or dispatcher.resolve_used_update_types():
        observer: TelegramEventObserver = getattr(dispatcher, allowed_update)
        observer.middleware(DIMiddleware())

    dispatcher["di_manager"] = di_manager = DIManager(
        dependency_overrides=(dependency_overrides or {})
    )
    return di_manager
