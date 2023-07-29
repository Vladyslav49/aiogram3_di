from collections.abc import Callable, Awaitable
from contextlib import AsyncExitStack
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from .utils import process_dependencies


class DIMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: dict[str, Any]
    ) -> Any:
        async with AsyncExitStack() as stack:
            data = await process_dependencies(stack, data.copy())
            return await handler(event, data)
