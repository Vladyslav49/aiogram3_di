import logging
from os import getenv
from typing import Annotated

from aiogram import Router, Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message, User
from aiogram3_di import setup_di, Depends

router = Router()


class MissingLastNameError(Exception):
    pass


async def check_last_name_presence(event: Message) -> None:
    if event.from_user.last_name is None:
        await event.answer(
            "Before you write to me, you must include your last name in your profile."
        )
        raise MissingLastNameError("User does not have a last name")


def get_user_full_name(event_from_user: User) -> str:
    return event_from_user.full_name


@router.message(
    CommandStart(), flags={"dependencies": [Depends(check_last_name_presence)]}
)
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
