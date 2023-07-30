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


def _is_coroutine_callable(call: Callable[..., Any]) -> bool:
    if inspect.isroutine(call):
        return inspect.iscoroutinefunction(call)
    if inspect.isclass(call):
        return False
    dunder_call = getattr(call, '__call__', None)
    return inspect.iscoroutinefunction(dunder_call)


def _is_async_gen_callable(call: Callable[..., Any]) -> bool:
    if inspect.isasyncgenfunction(call):
        return True
    dunder_call = getattr(call, '__call__', None)
    return inspect.isasyncgenfunction(dunder_call)


def _is_gen_callable(call: Callable[..., Any]) -> bool:
    if inspect.isgeneratorfunction(call):
        return True
    dunder_call = getattr(call, '__call__', None)
    return inspect.isgeneratorfunction(dunder_call)


async def __process_dependency(
        cache: dict[int, Any],
        call: Callable[..., Any],
        dependency: Depends,
        stack: AsyncExitStack,
        data: dict[str, Any],
        param_data: dict[tuple[int, str], Any]
) -> Any:
    if (cached_value := cache.get(hash(call))) and dependency.use_cache:
        return cached_value

    values = _get_valid_kwargs((data | _extract_params(inspect.getfullargspec(call).annotations, param_data)), call)

    if _is_async_gen_callable(call):
        cm = asynccontextmanager(call)(**values)
        result = await stack.enter_async_context(cm)
    elif _is_gen_callable(call):
        cm = _contextmanager_in_threadpool(contextmanager(call)(**values))
        result = await stack.enter_async_context(cm)
    elif _is_coroutine_callable(call):
        result = await call(**values)
    else:
        result = await asyncio.to_thread(call, **values)
    cache.setdefault(hash(dependency.func), result)
    return result


async def _process_dependency(
        cache: dict[int, Any],
        stack: AsyncExitStack,
        data: dict[str, Any],
        param_data: dict[tuple[int, str], Any],
        dependency: Depends,
        type_annotation: Any,
        param_name: str
) -> None:
    call = dependency.func or type_annotation
    result = await __process_dependency(cache, call, dependency, stack, data, param_data)
    param_data[(hash(call)), param_name] = result


async def _process_global_dependency(
        cache: dict[int, Any],
        stack: AsyncExitStack,
        data: dict[str, Any],
        param_data: dict[tuple[int, str], Any],
        dependency: Depends
) -> None:
    for param_name, sub_dependency, type_annotation in _get_dependencies(inspect.getfullargspec(dependency.func).annotations):
        await _process_dependency(cache, stack, data, param_data, sub_dependency, type_annotation, param_name)

    await __process_dependency(cache, dependency.func, dependency, stack, data, param_data)


async def process_dependencies(
        stack: AsyncExitStack,
        global_dependencies: list[Depends],
        handler_dependencies: list[Depends],
        data: dict[str, Any]
) -> dict[str, Any]:
    param_data: dict[tuple[int, str], Any] = {}
    cache: dict[int, Any] = {}

    for global_dependency in (global_dependencies + handler_dependencies):
        await _process_global_dependency(cache, stack, data, param_data, global_dependency)

    for param_name, dependency, type_annotation in _get_dependencies(data['handler'].spec.annotations):
        await _process_dependency(cache, stack, data, param_data, dependency, type_annotation, param_name)

    return data | _extract_params(data['handler'].spec.annotations, param_data)
