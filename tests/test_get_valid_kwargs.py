from typing import Annotated

from aiogram.types import Message, User, TelegramObject

from aiogram3_di import Depends
from aiogram3_di.utils import get_valid_kwargs


def get_user_full_name(event_from_user: User) -> str:
    return event_from_user.full_name


async def start(
    message: Message,
    full_name: Annotated[str, Depends(get_user_full_name)],
) -> None:
    await message.answer(f"Hi {full_name}")


def test_get_valid_kwargs() -> None:
    middleware_data = {}
    event = TelegramObject()
    params: dict[str, str] = {
        "first_name": "Vladyslav",
        "last_name": "Timofeev",
        "full_name": "Vladyslav Timofeev",
    }
    data = middleware_data | {"event": event} | params

    kwargs = get_valid_kwargs(data, start)

    assert kwargs == {"full_name": "Vladyslav Timofeev"}
