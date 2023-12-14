import logging
import random
from collections.abc import Iterator
from contextlib import AbstractContextManager
from os import getenv
from types import TracebackType
from typing import Annotated

from aiogram import Router, Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram3_di import setup_di, Depends

router = Router()


class ContextManager(AbstractContextManager):
    def __init__(self) -> None:
        self._closed = False

    def get_random_number(self) -> int:
        if self._closed:
            raise ValueError("Context manager is closed")
        return random.randint(1, 10)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._closed = True


def get_context_manager() -> Iterator[ContextManager]:
    with ContextManager() as context_manager:
        yield context_manager


@router.message(CommandStart())
async def start(
    message: Message,
    context_manager: Annotated[ContextManager, Depends(get_context_manager)],
) -> None:
    number = context_manager.get_random_number()
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
