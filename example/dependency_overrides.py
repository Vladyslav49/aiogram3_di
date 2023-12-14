import logging
from os import getenv
from typing import Annotated

from aiogram import Router, Bot, Dispatcher
from aiogram.types import Message, User
from aiogram3_di import setup_di, Depends

router = Router()


def get_user_full_name(event_from_user: User) -> str:
    return event_from_user.full_name


@router.message()
async def start(
    message: Message, full_name: Annotated[str, Depends(get_user_full_name)]
) -> None:
    assert message.from_user.username == full_name
    await message.answer(f"Hi {full_name}")


def get_user_username(event_from_user: User) -> str | None:
    return event_from_user.username


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=getenv("BOT_TOKEN"))

    dp = Dispatcher()

    dp.include_router(router)

    setup_di(dp, dependency_overrides={get_user_full_name: get_user_username})

    dp.run_polling(bot)


if __name__ == "__main__":
    main()
