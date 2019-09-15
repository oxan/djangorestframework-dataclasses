import dataclasses
import inspect
import typing
from collections import namedtuple

from rest_framework.utils.model_meta import RelationInfo

from rest_framework_dataclasses import typing_utils

T = typing.TypeVar('T')

DataclassDefinition = namedtuple('DataclassDefinition', [
    'type',         # Dataclass type
    'fields',       # Dict of field name -> dataclass field instance
    'field_types'   # Dict of field name -> type hint
])

FieldInfo = namedtuple('FieldInfo', [
    'name',         # Field name
    'type',         # Underlying, bare type
    'is_many',      # Is this field iterable
    'is_mapping',   # Is this field a mapping
    'is_optional'   # Is this field optional
])

TypeInfo = namedtuple('TypeInfo', [
    'is_many',      # Is this type iterable
    'is_mapping',   # Is this type a mapping
    'is_optional',  # Is this type optional
    'base_type'     # Underlying base type
])


def get_dataclass_definition(dataclass_type: type) -> DataclassDefinition:
    """
    Given a dataclass class, returns a dictionary mapping field names to
    `dataclasses.Field` instances describing all fields on the dataclass.
    """
    # Resolve the typehint from the dataclass fields (which can be stringified, especially with PEP 563 nowadays) to
    # actual type objects. Based on the discussion in https://stackoverflow.com/a/55938344.
    types = typing.get_type_hints(dataclass_type)

    # Disable PyCharm warning here, as it is wrong.
    # noinspection PyDataclass
    fields = {field.name: field for field in dataclasses.fields(dataclass_type)}

    return DataclassDefinition(dataclass_type, fields, types)


def get_type_info(tp: type) -> TypeInfo:
    """
    Reduce iterable and optional types to their 'base' types.
    """
    is_mapping = typing_utils.is_mapping_type(tp)
    is_many = typing_utils.is_iterable_type(tp)

    if is_mapping:
        tp = typing_utils.get_mapping_value_type(tp)
    elif is_many:  # This must be elif (instead of if), as otherwise we'd reduce mappings twice
        tp = typing_utils.get_iterable_element_type(tp)

    is_optional = typing_utils.is_optional_type(tp)
    if is_optional:
        tp = typing_utils.get_optional_type(tp)

    return TypeInfo(is_many, is_mapping, is_optional, tp)


def get_field_info(definition: DataclassDefinition, field_name: str) -> FieldInfo:
    """
    Get the name and type information of a field.
    """
    type_hint = definition.field_types[field_name]
    type_info = get_type_info(type_hint)

    return FieldInfo(field_name, type_info.base_type, type_info.is_many, type_info.is_mapping, type_info.is_optional)


def get_relation_info(definition: DataclassDefinition, field_info: FieldInfo) -> RelationInfo:
    # TODO needs checks first
    return RelationInfo(
        model_field=None,
        related_model=field_info.type,
        to_many=field_info.is_many,
        to_field=None,
        has_through_model=False,
        reverse=False
    )


def lookup_type_in_mapping(mapping: typing.Dict[type, T], key: type) -> T:
    for cls in inspect.getmro(key):
        if cls in mapping:
            return mapping[cls]

    raise KeyError("Class '{cls}' not found in lookup.".format(cls=key))
