import inspect
from typing import Annotated

from aiogram import Router
from aiogram.types import Message, User

from aiogram3_di import Depends
from aiogram3_di.utils import get_dependencies

router = Router()


def get_user_full_name(event_from_user: User) -> str:
    return event_from_user.full_name


@router.message()
async def start(
        message: Message, full_name: Annotated[str, Depends(get_user_full_name)]
) -> None:
    await message.answer(f"Hi {full_name}")


def test_get_dependencies() -> None:
    dependencies = list(get_dependencies(inspect.get_annotations(start)))
    assert dependencies == [("full_name", Depends(get_user_full_name), str)]
