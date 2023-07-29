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


def _extract_params(annotations: dict[str, Any], param_data: dict[tuple[int, str], Any]) -> dict[str, Any]:
    dependencies: list[tuple[int, str]] = [(hash(value.__metadata__[0].func or value.__origin__), key) for key, value in annotations.items()
                                            if isinstance(value, _AnnotatedAlias) and isinstance(value.__metadata__[0], Depends)]
    return {param_name: param_data[(func_hash, param_name)] for func_hash, param_name in dependencies}


async def _process_dependency(
        cache: dict[int, Any],
        call: Callable[..., Any],
        use_cache: bool,
        stack: AsyncExitStack,
        data: dict[str, Any],
        param_data: dict[tuple[int, str], Any]
) -> Any:
    if (cached_value := cache.get(hash(call))) and use_cache:
        return cached_value

    values = _get_valid_kwargs((data | _extract_params(inspect.getfullargspec(call).annotations, param_data)), call)

    if inspect.isasyncgenfunction(call):
        cm = asynccontextmanager(call)(**values)
        return await stack.enter_async_context(cm)
    elif inspect.isgeneratorfunction(call):
        cm = _contextmanager_in_threadpool(contextmanager(call)(**values))
        return await stack.enter_async_context(cm)
    elif asyncio.iscoroutinefunction(call):
        return await call(**values)
    else:
        return await asyncio.to_thread(call, **values)


async def process_dependencies(stack: AsyncExitStack, data: dict[str, Any]) -> dict[str, Any]:
    param_data: dict[tuple[int, str], Any] = {}
    cache: dict[int, Any] = {}

    for param_name, dependency, type_annotation in _get_dependencies(data['handler'].spec.annotations):
        call = dependency.func or type_annotation
        result = await _process_dependency(cache, call, dependency.use_cache, stack, data, param_data)
        param_data[(hash(call)), param_name] = result
        cache.setdefault(hash(call), result)

    return data | _extract_params(data['handler'].spec.annotations, param_data)
