from __future__ import annotations

import dataclasses
import inspect

from typing import Any, Dict, Generic, Mapping, Optional, Type, TypeVar

from rest_framework.utils.model_meta import RelationInfo

from rest_framework_dataclasses import typing_utils
from rest_framework_dataclasses.types import Dataclass

T = TypeVar('T', bound=Dataclass)
AnyT = TypeVar('AnyT')


@dataclasses.dataclass
class DataclassDefinition(Generic[T]):
    dataclass_type: Type[T]
    fields: Dict[str, dataclasses.Field[Any]]
    field_types: Dict[str, type]


@dataclasses.dataclass
class TypeInfo:
    is_many: bool
    is_mapping: bool
    is_final: bool
    is_nullable: bool
    base_type: type
    container_type: Optional[type]


def get_dataclass_definition(dataclass_type: Type[T]) -> DataclassDefinition[T]:
    """
    Given a dataclass class, returns a dictionary mapping field names to
    `dataclasses.Field` instances describing all fields on the dataclass.
    """
    types = typing_utils.get_resolved_type_hints(dataclass_type)

    # Disable PyCharm warning here, as it is wrong.
    # noinspection PyDataclass
    fields = {field.name: field for field in dataclasses.fields(dataclass_type)}

    return DataclassDefinition(dataclass_type, fields, types)


def get_type_info(tp: type) -> TypeInfo:
    """
    Reduce iterable and optional types to their 'base' types.
    """
    is_final = typing_utils.is_final_type(tp)
    if is_final:
        tp = typing_utils.get_final_type(tp)
        if tp is Any:
            # This used to be supported, but Python 3.10 raises in get_type_hints() if it encounters a plain Final hint.
            raise TypeError('Plain typing.Final is not valid as a type argument.')

    is_nullable = typing_utils.is_optional_type(tp)
    if is_nullable:
        tp = typing_utils.get_optional_type(tp)

    is_mapping = typing_utils.is_mapping_type(tp)
    is_many = typing_utils.is_iterable_type(tp)

    cp = None
    if is_mapping or is_many:
        container_type = typing_utils.get_container_type(tp)
        if not inspect.isabstract(container_type):
            cp = container_type

    if is_mapping:
        tp = typing_utils.get_mapping_value_type(tp)
    elif is_many:  # This must be elif (instead of if), as otherwise we'd reduce mappings twice as they're also iterable
        tp = typing_utils.get_iterable_element_type(tp)

    if typing_utils.is_type_variable(tp):
        tp = typing_utils.get_variable_type_substitute(tp)

    return TypeInfo(is_many, is_mapping, is_final, is_nullable, tp, cp)


def get_relation_info(type_info: TypeInfo) -> RelationInfo:
    """
    Given a type_info that references a Model, extract the RelationInfo.
    """
    return RelationInfo(
        # there's no foreign key field
        model_field=None,
        related_model=type_info.base_type,
        to_many=type_info.is_many,
        # as there's no foreign key, it also cannot reference a field on the referenced model
        to_field='',
        has_through_model=False,
        # we're never the model
        reverse=False
    )


def lookup_type_in_mapping(mapping: Mapping[type, AnyT], key: type) -> AnyT:
    # Allow all types, including special forms, to be used when they're present in the mapping
    if key in mapping:
        return mapping[key]

    try:
        # _SpecialForm types like Literal, NoReturn don't have an __mro__ attribute
        bases = inspect.getmro(key)
    except AttributeError:
        raise KeyError("Special type {typ} not supported.".format(typ=key))

    for cls in bases:
        if cls in mapping:
            return mapping[cls]

    raise KeyError("Class '{cls}' not found in lookup.".format(cls=key))
