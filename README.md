### Example of usage

```python
import logging
from os import getenv
from typing import Annotated

from aiogram import Router, Bot, Dispatcher
from aiogram.types import Message
from aiogram3_di import DIMiddleware, Depends

router = Router()


def get_user_full_name(event: Message) -> str:
    return event.from_user.full_name


@router.message()
async def _(message: Message, full_name: Annotated[str, Depends(get_user_full_name)]) -> None:
    await message.answer(f'Hi {full_name}')


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=getenv('BOT_TOKEN'))

    dp = Dispatcher()
    dp.include_router(router)
    dp.message.middleware(DIMiddleware())  # register Dependency Injection middleware
    dp.run_polling(bot)


if __name__ == '__main__':
    main()
```

### Handler Dependencies.

You can use `Depends` in the flags parameter of the handler, for example: 

```python
flags={'dependencies': [Depends(verify_user)]}
```

### Global Dependencies.

You can use `Depends` in `dispatcher`, for example:

```python
dp = Dispatcher()
dp.dependencies = [Depends(verify_user)]
```

Or in `router`, for example:

```python
router = Router()
router.dependencies = [Depends(verify_user)]
```

### Details

It is inspired by [FastAPI](https://github.com/tiangolo/fastapi).

If you define a normal def, your function will be called in a different thread.

### License

MIT
