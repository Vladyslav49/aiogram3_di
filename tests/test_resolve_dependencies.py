from collections.abc import MutableSequence
from contextlib import AsyncExitStack
from typing import Annotated

import pytest
from aiogram import Dispatcher
from aiogram.dispatcher.event.handler import HandlerObject
from aiogram.types import Message, User, TelegramObject

from aiogram3_di import Depends, setup_di
from aiogram3_di.resolver import DependenciesResolver


def get_user_full_name(event_from_user: User) -> str:
    return event_from_user.full_name


async def start(
    message: Message, full_name: Annotated[str, Depends(get_user_full_name)]
) -> None:
    await message.answer(f"Hi {full_name}")


class MockedDependency:
    __slots__ = ("_call_args_list", "_return_value")

    def __init__(
        self, call_args_list: MutableSequence[str], *, return_value: str | None = None
    ) -> None:
        self._call_args_list = call_args_list
        self._return_value = return_value

    def __call__(self) -> str | None:
        self._call_args_list.append(self._return_value)
        return self._return_value


@pytest.mark.asyncio
async def test_resolve_dependencies(dp: Dispatcher) -> None:
    call_args_list = []
    mocked_verify_user = MockedDependency(call_args_list)
    mocked_get_user_full_name = MockedDependency(
        call_args_list, return_value="Vladyslav Timofeev"
    )
    setup_di(dp, dependency_overrides={get_user_full_name: mocked_get_user_full_name})
    handler_dependencies = (Depends(mocked_verify_user),)
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

    assert len(call_args_list) == 2
    assert call_args_list[0] is None
    assert call_args_list[1] == "Vladyslav Timofeev"
    assert middleware_data["full_name"] == "Vladyslav Timofeev"
