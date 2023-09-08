import asyncio
import inspect
from collections.abc import Callable
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from typing import Any

from .depends import Depends
from .utils import (
    ParamData,
    get_dependencies,
    extract_params,
    get_valid_kwargs,
    is_async_gen_callable,
    is_gen_callable,
    contextmanager_in_threadpool,
    is_coroutine_callable
)


class DependenciesResolver:

    __slots__ = (
        '_stack',
        '_global_dependencies',
        '_data',
        '_param_data',
        '_cache'
    )

    def __init__(
            self,
            stack: AsyncExitStack,
            global_dependencies: tuple[Depends, ...],
            handler_dependencies: tuple[Depends, ...],
            data: dict[str, Any]
    ) -> None:
        self._stack = stack
        self._global_dependencies = global_dependencies + handler_dependencies
        self._data = data
        self._param_data: ParamData = {}
        self._cache: dict[int, Any] = {}

    async def resolve(self) -> dict[str, Any]:
        for global_dependency in self._global_dependencies:
            await self._resolve_global_dependency(global_dependency)

        for param_name, dependency, type_annotation in get_dependencies(self._data['handler'].spec.annotations):
            await self._process_dependency(param_name, dependency, type_annotation)

        del self._data['event']

        return self._data | extract_params(self._data['handler'].spec.annotations, self._param_data)  # noqa: E501

    async def _resolve_global_dependency(self, dependency: Depends) -> None:
        for param_name, sub_dependency, type_annotation in get_dependencies(inspect.get_annotations(dependency.func)):
            await self._process_dependency(param_name, sub_dependency, type_annotation)

        await self.__process_dependency(dependency.func, dependency)

    async def _process_dependency(
            self, param_name: str, dependency: Depends, type_annotation: Any
    ) -> None:
        call = dependency.func or type_annotation
        result = await self.__process_dependency(call, dependency)
        self._param_data[(hash(call)), param_name] = result

    async def __process_dependency(
            self, call: Callable[..., Any], dependency: Depends
    ) -> Any:
        if (cached_value := self._cache.get(hash(call))) and dependency.use_cache:
            return cached_value

        params = extract_params(inspect.get_annotations(call), self._param_data)
        values = get_valid_kwargs((self._data | params), call)

        if is_async_gen_callable(call):
            cm = asynccontextmanager(call)(**values)
            result = await self._stack.enter_async_context(cm)
        elif is_gen_callable(call):
            cm = contextmanager_in_threadpool(contextmanager(call)(**values))
            result = await self._stack.enter_async_context(cm)
        elif is_coroutine_callable(call):
            result = await call(**values)
        else:
            result = await asyncio.to_thread(call, **values)
        self._cache.setdefault(hash(dependency.func), result)
        return result
