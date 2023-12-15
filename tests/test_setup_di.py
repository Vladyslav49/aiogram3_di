from aiogram import Dispatcher

from aiogram3_di import setup_di
from aiogram3_di.middleware import DIMiddleware


def test_setup_di(dp: Dispatcher) -> None:
    di_manager = setup_di(dp, allowed_updates=["message"])

    assert dp["di_manager"] == di_manager
    assert di_manager.dependency_overrides == {}
    assert any(
        isinstance(middleware, DIMiddleware) for middleware in dp.message.middleware
    )
    assert not any(
        isinstance(middleware, DIMiddleware)
        for middleware in dp.callback_query.middleware
    )
