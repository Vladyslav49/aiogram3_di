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
            data: dict[str, Any]
    ) -> Any:
        dispatcher_dependencies = tuple(getattr(data['dispatcher'], 'dependencies', ()))
        router_dependencies = tuple(getattr(data['event_router'], 'dependencies', ()))
        handler_dependencies = tuple(get_flag(data, 'dependencies', default=()))

        async with AsyncExitStack() as stack:
            resolver = DependenciesResolver(stack, (dispatcher_dependencies + router_dependencies),
                                            handler_dependencies, (data.copy() | {'event': event}))
            data = await resolver.resolve()
            return await handler(event, data)
