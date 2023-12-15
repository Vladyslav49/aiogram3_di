import pytest
from aiogram import Dispatcher


@pytest.fixture()
def dp() -> Dispatcher:
    return Dispatcher()
