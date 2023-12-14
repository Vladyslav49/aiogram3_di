import asyncio
import inspect
from collections.abc import Iterator, Callable
from contextlib import asynccontextmanager
from typing import Any, _AnnotatedAlias, get_args, ContextManager, TypeAlias

from .depends import Depends

ParamData: TypeAlias = dict[tuple[int, str], Any]


def get_valid_kwargs(data: dict[str, Any], func: Callable[..., Any]) -> dict[str, Any]:
    valid_params = [param.name for param in inspect.signature(func).parameters.values()
                    if param.default == inspect.Parameter.empty]
    return {key: value for key, value in data.items() if key in valid_params}


def get_dependencies(annotations: dict[str, Any]) -> Iterator[tuple[str, Depends, Any]]:
    for annotation_key, annotation_value in annotations.items():
        if isinstance(annotation_value, inspect.Parameter):
            annotation_value = annotation_value.annotation

        if isinstance(annotation_value, _AnnotatedAlias):
            type_annotation, dependency = get_args(annotation_value)[:2]
            if isinstance(dependency, Depends):
                if parameters := inspect.signature(dependency.func or type_annotation).parameters:
                    yield from get_dependencies(dict(parameters))
                yield annotation_key, dependency, type_annotation


@asynccontextmanager
async def contextmanager_in_threadpool(cm: ContextManager):
    try:
        yield await asyncio.to_thread(cm.__enter__)
    except Exception as e:
        ok = bool(await asyncio.to_thread(cm.__exit__, type(e), e, None))
        if not ok:
            raise e
    else:
        await asyncio.to_thread(cm.__exit__, None, None, None)


def extract_params(annotations: dict[str, Any], param_data: ParamData) -> dict[str, Any]:  # noqa: E501
    dependencies: list[tuple[int, str]] = [(hash(value.__metadata__[0].func or value.__origin__), key) for key, value in annotations.items()
                                            if isinstance(value, _AnnotatedAlias) and isinstance(value.__metadata__[0], Depends)]
    return {param_name: param_data[(func_hash, param_name)] for func_hash, param_name in dependencies}  # noqa: E501


def is_coroutine_callable(call: Callable[..., Any]) -> bool:
    if inspect.isroutine(call):
        return inspect.iscoroutinefunction(call)
    if inspect.isclass(call):
        return False
    dunder_call = getattr(call, '__call__', None)
    return inspect.iscoroutinefunction(dunder_call)


def is_async_gen_callable(call: Callable[..., Any]) -> bool:
    if inspect.isasyncgenfunction(call):
        return True
    dunder_call = getattr(call, '__call__', None)
    return inspect.isasyncgenfunction(dunder_call)


def is_gen_callable(call: Callable[..., Any]) -> bool:
    if inspect.isgeneratorfunction(call):
        return True
    dunder_call = getattr(call, '__call__', None)
    return inspect.isgeneratorfunction(dunder_call)
