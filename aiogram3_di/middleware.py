from collections.abc import Callable, Awaitable
from contextlib import AsyncExitStack
from typing import Any

from aiogram import BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.types import TelegramObject

from .utils import process_dependencies


class DIMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: dict[str, Any]
    ) -> Any:
        dispatcher_dependencies = list(getattr(data['dispatcher'], 'dependencies', []))
        router_dependencies = list(getattr(data['event_router'], 'dependencies', []))
        handler_dependencies = list(get_flag(data, 'dependencies', default=[]))

        async with AsyncExitStack() as stack:
            data = await process_dependencies(stack, (dispatcher_dependencies + router_dependencies),
                                              handler_dependencies, data.copy())
            return await handler(event, data)
