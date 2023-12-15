from contextlib import AsyncExitStack
from typing import Annotated

import pytest
from aiogram import Dispatcher
from aiogram.types import Message, User, TelegramObject

from aiogram3_di import Depends, setup_di
from aiogram3_di.resolver import DependenciesResolver


def get_user_full_name(event_from_user: User) -> str:
    return event_from_user.full_name


async def start(
    message: Message, full_name: Annotated[str, Depends(get_user_full_name)]
) -> None:
    await message.answer(f"Hi {full_name}")


def get_username(event_from_user: User) -> str:
    return event_from_user.username


@pytest.mark.asyncio
async def test_dependency_overrides(dp: Dispatcher) -> None:
    setup_di(dp, dependency_overrides={get_user_full_name: get_username})
    handler_dependencies = ()
    event = TelegramObject()
    middleware_data = dp.workflow_data

    async with AsyncExitStack() as stack:
        resolver = DependenciesResolver(
            stack,
            handler_dependencies=handler_dependencies,
            event=event,
            middleware_data=middleware_data,
        )
        call = resolver._get_call(
            dependency=Depends(get_user_full_name), type_annotation=str
        )

    assert call == get_username
