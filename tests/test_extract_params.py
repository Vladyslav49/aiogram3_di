import inspect
import time
from contextlib import AsyncExitStack
from typing import Annotated

import pytest
from aiogram import Dispatcher
from aiogram.dispatcher.event.handler import HandlerObject
from aiogram.enums import ChatType
from aiogram.types import Message, Chat, User

from aiogram3_di import Depends, setup_di
from aiogram3_di.resolver import DependenciesResolver


def get_user_full_name(event: Message) -> str:
    return event.from_user.full_name


async def start(
    message: Message, full_name: Annotated[str, Depends(get_user_full_name)]
) -> None:
    await message.answer(f"Hi {full_name}")


@pytest.mark.asyncio
async def test_extract_params(dp: Dispatcher) -> None:
    setup_di(dp)
    handler_dependencies = ()
    event = Message(
        message_id=0,
        date=time.time(),
        chat=Chat(id=0, type=ChatType.PRIVATE),
        from_user=User(
            id=0, is_bot=False, first_name="Vladyslav", last_name="Timofeev"
        ),
    )
    middleware_data = dp.workflow_data | {"handler": HandlerObject(start)}

    async with AsyncExitStack() as stack:
        resolver = DependenciesResolver(
            stack,
            handler_dependencies=handler_dependencies,
            event=event,
            middleware_data=middleware_data,
        )
        resolver._param_data = {
            (hash(get_user_full_name), "full_name"): "Vladyslav Timofeev"
        }
        params = resolver._extract_params(inspect.get_annotations(start))

    assert params == {"full_name": "Vladyslav Timofeev"}
