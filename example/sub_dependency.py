import logging
from os import getenv
from typing import Annotated

from aiogram import Router, Bot, Dispatcher
from aiogram.types import Message, User
from aiogram3_di import setup_di, Depends

router = Router()


def get_user_first_name(event_from_user: User) -> str:
    return event_from_user.first_name


def get_user_last_name(event_from_user: User) -> str | None:
    return event_from_user.last_name


def get_user_full_name(
    first_name: Annotated[str, Depends(get_user_first_name)],
    last_name: Annotated[str | None, Depends(get_user_last_name)],
) -> str:
    if last_name is not None:
        return f"{first_name} {last_name}"
    return first_name


@router.message()
async def start(
    message: Message, full_name: Annotated[str, Depends(get_user_full_name)]
) -> None:
    await message.answer(f"Hi {full_name}")


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=getenv("BOT_TOKEN"))

    dp = Dispatcher()

    dp.include_router(router)

    setup_di(dp)

    dp.run_polling(bot)


if __name__ == "__main__":
    main()
