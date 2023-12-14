import inspect
from typing import Annotated

from aiogram import Router
from aiogram.types import Message, User

from aiogram3_di import Depends
from aiogram3_di.utils import get_dependencies

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


def test_get_sub_dependencies() -> None:
    dependencies = list(get_dependencies(inspect.get_annotations(start)))
    assert dependencies == [
        ("first_name", Depends(get_user_first_name), str),
        ("last_name", Depends(get_user_last_name), str | None),
        ("full_name", Depends(get_user_full_name), str),
    ]
