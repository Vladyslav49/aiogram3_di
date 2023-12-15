from contextlib import AsyncExitStack
from typing import Annotated
from unittest.mock import Mock

import pytest
from aiogram import Dispatcher
from aiogram.dispatcher.event.handler import HandlerObject
from aiogram.types import Message, User, TelegramObject

from aiogram3_di import Depends, setup_di
from aiogram3_di.resolver import DependenciesResolver


def get_user_full_name(event_from_user: User) -> str:
    return event_from_user.full_name


async def start(
    message: Message,
    full_name: Annotated[str, Depends(get_user_full_name, use_cache=False)],
) -> None:
    await message.answer(f"Hi {full_name}")


@pytest.mark.asyncio
async def test_disable_cache(dp: Dispatcher) -> None:
    mocked_get_user_full_name = Mock(
        side_effect=["Vladyslav Timofeev", "Vlad Timofeev"]
    )
    setup_di(dp, dependency_overrides={get_user_full_name: mocked_get_user_full_name})
    handler_dependencies = (Depends(get_user_full_name),)
    event = TelegramObject()
    middleware_data = dp.workflow_data | {"handler": HandlerObject(start)}

    async with AsyncExitStack() as stack:
        resolver = DependenciesResolver(
            stack,
            handler_dependencies=handler_dependencies,
            event=event,
            middleware_data=middleware_data,
        )
        middleware_data = await resolver.resolve()

    assert mocked_get_user_full_name.call_count == 2
    assert middleware_data["full_name"] == "Vlad Timofeev"
    assert resolver._cache == {hash(mocked_get_user_full_name): "Vladyslav Timofeev"}
