import logging
import random
from collections.abc import Iterator
from contextlib import AbstractAsyncContextManager
from os import getenv
from types import TracebackType
from typing import Annotated

from aiogram import Router, Bot, Dispatcher
from aiogram.types import Message
from aiogram3_di import setup_di, Depends

router = Router()


class AsyncContextManager(AbstractAsyncContextManager):
    def __init__(self) -> None:
        self._closed = False

    def get_random_number(self) -> int:
        if self._closed:
            raise ValueError("Async context manager is closed")
        return random.randint(1, 10)

    async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
    ) -> None:
        self._closed = True


async def get_async_context_manager() -> Iterator[AsyncContextManager]:
    async with AsyncContextManager() as context_manager:
        yield context_manager


@router.message()
async def start(
        message: Message,
        async_context_manager: Annotated[AsyncContextManager, Depends(get_async_context_manager)],
) -> None:
    number = async_context_manager.get_random_number()
    await message.answer(f"Number: {number}")


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=getenv("BOT_TOKEN"))

    dp = Dispatcher()

    dp.include_router(router)

    setup_di(dp)

    dp.run_polling(bot)


if __name__ == "__main__":
    main()
