from collections.abc import Callable, Awaitable
from contextlib import AsyncExitStack
from typing import Any

from aiogram import BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.types import TelegramObject

from .resolver import DependenciesResolver


class DIMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: dict[str, Any],
    ) -> Any:
        handler_dependencies = tuple(get_flag(data, "dependencies", default=()))

        async with AsyncExitStack() as stack:
            resolver = DependenciesResolver(
                stack,
                handler_dependencies=handler_dependencies,
                event=event,
                middleware_data=data.copy(),
            )
            data = await resolver.resolve()
            return await handler(event, data)
