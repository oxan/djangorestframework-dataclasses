"""
Abstract away the runtime introspection on type hints behind an at least mostly-sane interface.

Unfortunately, Python does not really have an API for that. As such, we're mostly poking around in the internals of the
typing module and use heuristics that seem to work for common type hints. There's fairly extensive test coverage to both
document what should be supported here, and to see what needs to be fixed for a new Python version.

Requirements for this module:

  * Support for Python 3.7 - 3.9
  * Support both immediate and postponed evaluation of annotations (PEP 563, i.e. `from __future__ import annotations`)
  * Support collection generics from the typing module (i.e. typing.List[int])
  * Support standard collection generics (PEP 585, i.e. list[int])

Note that there was some promising development in the `typing_inspect` module, but it is still marked experimental and
development seems to have stalled. Maybe in the future?
"""
import collections
import typing

from .types import Final, Literal

# typing._BaseGenericAlias was split-out from GenericAlias in Python 3.9
if hasattr(typing, '_BaseGenericAlias'):
    GenericAlias = typing._BaseGenericAlias
else:
    GenericAlias = typing._GenericAlias

# Wrappers around typing.get_origin() and typing.get_args() for Python 3.7
try:
    get_origin = typing.get_origin
    get_args = typing.get_args
except AttributeError:
    def get_origin(tp: type) -> type:
        return tp.__origin__ if isinstance(tp, GenericAlias) else None

    def get_args(tp: type) -> type:
        return tp.__args__ if isinstance(tp, GenericAlias) else ()

# Some implementation notes:
# * We detect if types are a generic by whether their origin is not None.
# * Some origins (most notably literals) aren't a type, so before doing issubclass() on an origin, we need to check
#   if it's a type.


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
    # * and at least one argumen that isn't NoneType
    # except for Literals (sigh), which are just regular Literals with None as an allowed value.
    origin = get_origin(tp)
    args = get_args(tp)
    none_type = type(None)
    return (
        origin is not None and
        origin is typing.Union and
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

    return next(argument_type for argument_type in get_args(tp) if argument_type is not type(None))


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


def get_variable_type_substitute(tp: typing.TypeVar) -> type:
    """
    Get the substitute for a variable type.
    """
    if len(tp.__constraints__) > 0:
        return typing.Union[tp.__constraints__]
    if tp.__bound__ is not None:
        return tp.__bound__
    return typing.Any
