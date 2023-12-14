import asyncio
import inspect
from collections.abc import Callable
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from typing import Any, TypeAlias, _AnnotatedAlias

from aiogram.dispatcher.event.handler import HandlerObject
from aiogram.types import TelegramObject

from .depends import Depends
from .manager import DIManager
from .utils import (
    get_dependencies,
    get_valid_kwargs,
    is_async_gen_callable,
    is_gen_callable,
    contextmanager_in_threadpool,
    is_coroutine_callable,
)

ParamData: TypeAlias = dict[tuple[int, str], Any]

CACHE_MISSING = object()


class DependenciesResolver:
    __slots__ = (
        "_stack",
        "_handler_dependencies",
        "_event",
        "_middleware_data",
        "_param_data",
        "_cache",
    )

    def __init__(
        self,
        stack: AsyncExitStack,
        *,
        handler_dependencies: tuple[Depends, ...],
        event: TelegramObject,
        middleware_data: dict[str, Any],
    ) -> None:
        self._stack = stack
        self._handler_dependencies = handler_dependencies
        self._event = event
        self._middleware_data = middleware_data
        self._param_data: ParamData = {}
        self._cache: dict[int, Any] = {}

    async def resolve(self) -> dict[str, Any]:
        for handler_dependency in self._handler_dependencies:
            await self._resolve_handler_dependency(handler_dependency)

        handler: HandlerObject = self._middleware_data["handler"]
        handler_annotations = inspect.get_annotations(handler.callback)

        for param_name, dependency, type_annotation in get_dependencies(
            handler_annotations
        ):
            await self._process_dependency(param_name, dependency, type_annotation)

        return self._middleware_data | self._extract_params(handler_annotations)

    def _extract_params(self, annotations: dict[str, Any]) -> dict[str, Any]:
        dependencies: list[tuple[int, str]] = []

        for param_name, param_value in annotations.items():
            if isinstance(param_value, _AnnotatedAlias) and isinstance(
                param_value.__metadata__[0], Depends
            ):
                dependency: Depends = param_value.__metadata__[0]
                type_annotation: Any = param_value.__origin__
                call = self._get_call(dependency, type_annotation)
                dependencies.append((hash(call), param_name))

        return {
            param_name: self._param_data[(func_hash, param_name)]
            for func_hash, param_name in dependencies
        }

    async def _resolve_handler_dependency(self, dependency: Depends) -> None:
        for param_name, sub_dependency, type_annotation in get_dependencies(
            inspect.get_annotations(dependency.func)
        ):
            await self._process_dependency(param_name, sub_dependency, type_annotation)

        call = self._get_call(dependency, None)
        await self.__process_dependency(call, dependency)

    async def _process_dependency(
        self, param_name: str, dependency: Depends, type_annotation: Any
    ) -> None:
        call = self._get_call(dependency, type_annotation)
        result = await self.__process_dependency(call, dependency)
        self._param_data[(hash(call)), param_name] = result

    def _get_call(
        self, dependency: Depends, type_annotation: Any
    ) -> Callable[..., Any]:
        original_call = dependency.func or type_annotation
        di_manager: DIManager = self._middleware_data["di_manager"]
        call = di_manager.dependency_overrides.get(original_call, original_call)
        return call

    async def __process_dependency(
        self, call: Callable[..., Any], dependency: Depends
    ) -> Any:
        cached_value = self._cache.get(hash(call), CACHE_MISSING)

        if cached_value is not CACHE_MISSING and dependency.use_cache:
            return cached_value

        params = self._extract_params(inspect.get_annotations(call))
        values = get_valid_kwargs(
            (self._middleware_data | {"event": self._event} | params), call
        )

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
        self._cache.setdefault(hash(call), result)
        return result
