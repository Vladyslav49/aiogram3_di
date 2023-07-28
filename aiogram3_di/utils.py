import asyncio
import inspect
from collections.abc import Iterator, Callable
from contextlib import asynccontextmanager, contextmanager, AsyncExitStack
from typing import Any, _AnnotatedAlias, get_args, ContextManager

from .depends import Depends


def _get_valid_kwargs(data: dict[str, Any], func: Callable[..., Any]) -> dict[str, Any]:
    valid_params = [param.name for param in inspect.signature(func).parameters.values()
                    if param.default == inspect.Parameter.empty]
    return {key: value for key, value in data.items() if key in valid_params}


def _get_dependencies(annotations: dict[str, Any]) -> Iterator[tuple[str, Depends]]:
    for annotation_key, annotation_value in annotations.items():
        if isinstance(annotation_value, inspect.Parameter):
            annotation_value = annotation_value.annotation

        if isinstance(annotation_value, _AnnotatedAlias):
            type_annotation, dependency = get_args(annotation_value)[:2]
            if isinstance(dependency, Depends):
                if parameters := inspect.signature(dependency.func or type_annotation).parameters:
                    yield from _get_dependencies(dict(parameters))
                yield annotation_key, dependency, type_annotation


@asynccontextmanager
async def _contextmanager_in_threadpool(cm: ContextManager):
    try:
        yield await asyncio.to_thread(cm.__enter__)
    except Exception as e:
        ok = bool(await asyncio.to_thread(cm.__exit__, type(e), e, None))
        if not ok:
            raise e
    else:
        await asyncio.to_thread(cm.__exit__, None, None, None)


async def process_dependencies(data: dict[str, Any]) -> dict[str, Any]:
    param_data: dict[tuple[int, str], Any] = {}
    cache: dict[int, Any] = {}

    async with AsyncExitStack() as stack:
        for param_name, dependency, type_annotation in _get_dependencies(data['handler'].spec.annotations):
            call = dependency.func or type_annotation

            if (cached_value := cache.get(hash(call))) and dependency.use_cache:
                result = cached_value
            else:
                func_dependencies: list[tuple[int, str]] = [(hash(value.__metadata__[0].func or value.__origin__), key) for key, value in inspect.getfullargspec(call).annotations.items()
                                                             if isinstance(value, _AnnotatedAlias) and isinstance(value.__metadata__[0], Depends)]
                values = _get_valid_kwargs(data | {param_name: param_data[(func_hash, param_name)] for func_hash, param_name in func_dependencies}, call)

                if inspect.isasyncgenfunction(call):
                    cm = asynccontextmanager(call)(**values)
                    result = await stack.enter_async_context(cm)
                elif inspect.isgeneratorfunction(call):
                    cm = _contextmanager_in_threadpool(contextmanager(call)(**values))
                    result = await stack.enter_async_context(cm)
                elif asyncio.iscoroutinefunction(call):
                    result = await call(**values)
                else:
                    result = await asyncio.to_thread(call, **values)

            param_data[(hash(call)), param_name] = result
            cache.setdefault(hash(call), result)
    handler_dependencies: list[tuple[int, str]] = [(hash(value.__metadata__[0].func or value.__origin__), key) for key, value in data['handler'].spec.annotations.items()
                                                    if isinstance(value, _AnnotatedAlias) and isinstance(value.__metadata__[0], Depends)]
    return data | {param_name: param_data[(func_hash, param_name)] for func_hash, param_name in handler_dependencies}
