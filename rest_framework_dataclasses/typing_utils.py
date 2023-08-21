from __future__ import annotations

"""
Abstract away the runtime introspection on type hints behind an at least mostly-sane interface.

Unfortunately, Python does not really have an API for that. As such, we're mostly poking around in the internals of the
typing module and use heuristics that seem to work for common type hints. There's fairly extensive test coverage to both
document what should be supported here, and to see what needs to be fixed for a new Python version.

Requirements for this module:

  * Support for Python 3.7 and above
  * Support both immediate and postponed evaluation of annotations (PEP 563, i.e. `from __future__ import annotations`)
  * Support collection generics from the typing module (i.e. typing.List[int])
  * Support standard collection generics (PEP 585, i.e. list[int])
  * Support pipe operator syntax for unions (PEP 604, i.e. int | str)

Note that there was some promising development in the `typing_inspect` module, but it is still marked experimental and
development seems to have stalled. Maybe in the future?
"""
import collections.abc
import sys
import types
import typing

from .types import Final, Literal

# types.UnionType was added in Python 3.10 for new PEP 604 pipe union syntax
if sys.version_info >= (3, 10):
    UNION_TYPES = (typing.Union, types.UnionType)
else:
    UNION_TYPES = (typing.Union,)

# typing.get_origin() and typing.get_args() were added in Python 3.8
if sys.version_info >= (3, 8):
    get_origin = typing.get_origin
    get_args = typing.get_args
else:
    # This is only for Python 3.7, so we don't have to worry about typing._BaseGenericAlias
    def get_origin(tp: type) -> type:
        return tp.__origin__ if isinstance(tp, typing._GenericAlias) else None

    def get_args(tp: type) -> typing.Tuple:
        return tp.__args__ if isinstance(tp, typing._GenericAlias) else ()

# Some implementation notes:
# * We detect if types are a generic by whether their origin is not None.
# * Some origins (most notably literals) aren't a type, so before doing issubclass() on an origin, we need to check
#   if it's a type.


def get_resolved_type_hints(tp: type) -> typing.Dict[str, type]:
    """
    Get the resolved type hints of an object.

    Resolving the type hints means converting any stringified type hint into an actual type object. These can come from
    either forward references (PEP 484), or postponed evaluation (PEP 563).
    """
    # typing.get_type_hints() does the heavy lifting for us, except when using PEP 585 generic types that contain a
    # stringified type hint (see https://bugs.python.org/issue41370)
    def _resolve_type(context_type: type, resolve_type: typing.Union[str, type]) -> type:
        if isinstance(resolve_type, str):
            globalsns = sys.modules[context_type.__module__].__dict__
            return globalsns.get(resolve_type, resolve_type)
        else:
            return _resolve_type_hint(context_type, resolve_type)

    def _resolve_type_hint(context_type: type, resolve_type: type) -> type:
        if not hasattr(types, 'GenericAlias') or not isinstance(resolve_type, types.GenericAlias):
            return resolve_type

        args = tuple(_resolve_type(context_type, arg) for arg in resolve_type.__args__)
        return typing.cast(type, types.GenericAlias(resolve_type.__origin__, args))

    return {k: _resolve_type_hint(tp, v) for k, v in typing.get_type_hints(tp).items()}


def is_iterable_type(tp: type) -> bool:
    """
    Test if the given type is iterable.

    Some examples of iterable type hints are:

        Iterable[str]
        Collection[str]
        Mapping[str, int]
        Sequence[str]
        List[str]
        Set[str]
        Dict[str, int]
        Generator[str, int, int]

    """
    # Iterables are a generic with an origin that is a subclass of Iterable.
    origin = get_origin(tp)
    return (
        origin is not None and
        isinstance(origin, type) and
        issubclass(origin, collections.abc.Iterable)
    )


def get_container_type(tp: type) -> typing.Optional[type]:
    """
    Return the unsubscripted container type of the given type.

    Some examples of container types are:

        Iterable[str] -> Iterable
        List[str] -> list
        Dict[str, int] -> dict

    """
    return get_origin(tp)


def get_iterable_element_type(tp: type) -> type:
    """
    Get the type of elements in an iterable.
    """
    if not is_iterable_type(tp):
        raise ValueError('get_iterable_element_type() called with non-iterable type.')

    args = get_args(tp)
    return args[0] if len(args) > 0 else typing.Any


def is_mapping_type(tp: type) -> bool:
    """
    Test if the given type is a mapping.

    Some examples of mapping type hints are:

        Mapping[str, int]
        Dict[str, int]

    """
    # Mappings are a generic with an origin that is a subclass of Mapping.
    origin = get_origin(tp)
    return (
        origin is not None and
        isinstance(origin, type) and
        issubclass(origin, collections.abc.Mapping)
    )


def get_mapping_value_type(tp: type) -> type:
    """
    Get the type of values in a mapping.
    """
    if not is_mapping_type(tp):
        raise ValueError('get_mapping_value_type() called with non-mapping type.')

    args = get_args(tp)
    return args[1] if len(args) == 2 else typing.Any


def is_optional_type(tp: type) -> bool:
    """
    Test if the given type is optional.

    Some examples of optional type hints are:

        Optional[int]
        Union[int, None]
        Literal[0, None]

    """
    # Optional types are:
    # * a generic
    # * with an origin of typing.Union (typing.Optional[int] reduces to typing.Union[int, None] at constructor time)
    # * with at least one argument that is NoneType
    # * and at least one argument that isn't NoneType
    # except for Literals (sigh), which are just regular Literals with None as an allowed value.
    origin = get_origin(tp)
    args = get_args(tp)
    none_type = type(None)
    return (
        origin is not None and
        origin in UNION_TYPES and
        any(argument_type is none_type for argument_type in args) and
        any(argument_type is not none_type for argument_type in args)
    ) or (
        is_literal_type(tp) and
        None in get_literal_choices(tp)
    )


def get_optional_type(tp: type) -> type:
    """
    Get the type that is made optional.
    """
    if not is_optional_type(tp):
        raise ValueError('get_optional_type() called with non-optional type.')

    if is_literal_type(tp):
        # Note that this doesn't remove `None` as a valid choice, but that's not a problem so far.
        return tp

    remaining_arguments = tuple(arg for arg in get_args(tp) if arg is not type(None))
    if len(remaining_arguments) == 1:
        return remaining_arguments[0]
    elif hasattr(types, 'UnionType') and isinstance(tp, types.UnionType):
        # The types in the `types` module can't be instantiated in a generic way. Luckily only types.UnionType is
        # relevant here, so handle it directly.
        return typing.Union[remaining_arguments]  # type: ignore
    else:
        return get_origin(tp)[remaining_arguments]  # type: ignore


def is_union_type(tp: type) -> bool:
    """
    Test if the given type is a union type type.
    """
    # Exclude unions of a single type with None, as they're considered optional types instead.
    none_type = type(None)
    return (
        get_origin(tp) in UNION_TYPES and
        sum(1 for member_type in get_args(tp) if member_type is not none_type) >= 2
    )


def get_union_choices(tp: type) -> typing.List[type]:
    """
    Get the possible values for a union type.
    """
    if not is_union_type(tp):
        raise ValueError('get_union_choices() called with non-union type.')

    none_type = type(None)
    return [tp for tp in get_args(tp) if tp is not none_type]


def is_literal_type(tp: type) -> bool:
    """
    Test if the given type is a literal expression.
    """
    # Stolen from typing_inspect
    origin = get_origin(tp)
    return tp is Literal or origin is Literal


def get_literal_choices(tp: type) -> typing.List[typing.Union[str, bytes, int, bool, None]]:
    """
    Get the possible values for a literal type.
    """
    if not is_literal_type(tp):
        raise ValueError('get_literal_choices() called with non-literal type.')

    # A Literal type may contain other Literals, so need to unnest those. This doesn't happen automatically like it
    # happens for Unions. For more details, see
    # https://www.python.org/dev/peps/pep-0586/#legal-parameters-for-literal-at-type-check-time
    values = []
    for value in get_args(tp):
        if is_literal_type(value):
            values.extend(get_literal_choices(value))
        else:
            values.append(value)
    return values


def is_final_type(tp: type) -> bool:
    """
    Test if the given type is a final type.
    """
    return tp is Final or get_origin(tp) is Final


def get_final_type(tp: type) -> type:
    """
    Get the type that is made final.
    """
    if not is_final_type(tp):
        raise ValueError('get_final_type() called with non-final type.')

    args = get_args(tp)
    return args[0] if len(args) > 0 else typing.Any


def is_type_variable(tp: type) -> bool:
    """
    Test if the given type is a variable type.
    """
    return isinstance(tp, typing.TypeVar)


def get_variable_type_substitute(tp: type) -> type:
    """
    Get the substitute for a variable type.
    """
    assert isinstance(tp, typing.TypeVar)

    if len(tp.__constraints__) > 0:
        return typing.Union[tp.__constraints__]  # type: ignore
    if tp.__bound__ is not None:
        return tp.__bound__
    return typing.Any  # type: ignore
