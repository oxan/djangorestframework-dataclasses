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

FieldInfo = namedtuple('TypeInfo', [
    'name',         # Field name
    'type',         # Underlying, bare type
    'is_many',      # Is this field iterable
    'is_mapping',   # Is this field a mapping
    'is_optional'   # Is this field optional
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


def get_field_info(definition: DataclassDefinition, field_name: str) -> FieldInfo:
    """
    Reduce iterable and optional types to their 'bare' types and flags for
    """
    tp = definition.field_types[field_name]

    is_mapping = typing_utils.is_mapping_type(tp)
    if is_mapping:
        tp = typing_utils.get_mapping_value_type(tp)

    is_many = typing_utils.is_iterable_type(tp)
    if is_many:
        tp = typing_utils.get_iterable_element_type(tp)

    is_optional = typing_utils.is_optional_type(tp)
    if is_optional:
        tp = typing_utils.get_optional_type(tp)

    return FieldInfo(field_name, tp, is_many, is_mapping, is_optional)


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
