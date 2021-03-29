import dataclasses
import inspect
import typing

from rest_framework.utils.model_meta import RelationInfo

from rest_framework_dataclasses import typing_utils

T = typing.TypeVar('T')


@dataclasses.dataclass
class DataclassDefinition:
    dataclass_type: type
    fields: typing.Dict[str, dataclasses.Field]
    field_types: typing.Dict[str, type]


@dataclasses.dataclass
class TypeInfo:
    is_many: bool
    is_mapping: bool
    is_final: bool
    is_nullable: bool
    base_type: type


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
    is_final = typing_utils.is_final_type(tp)
    if is_final:
        tp = typing_utils.get_final_type(tp)
        if tp is typing.Any:
            # This used to be supported, but Python 3.10 raises in get_type_hints() if it encounters a plain Final hint.
            raise TypeError('Plain typing.Final is not valid as a type argument.')

    is_nullable = typing_utils.is_optional_type(tp)
    if is_nullable:
        tp = typing_utils.get_optional_type(tp)

    is_mapping = typing_utils.is_mapping_type(tp)
    is_many = typing_utils.is_iterable_type(tp)

    if is_mapping:
        tp = typing_utils.get_mapping_value_type(tp)
    elif is_many:  # This must be elif (instead of if), as otherwise we'd reduce mappings twice as they're also iterable
        tp = typing_utils.get_iterable_element_type(tp)

    if typing_utils.is_type_variable(tp):
        tp = typing_utils.get_variable_type_substitute(tp)

    if tp is typing.Any:
        tp = None

    return TypeInfo(is_many, is_mapping, is_final, is_nullable, tp)


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
        to_field=None,
        has_through_model=False,
        # we're never the model
        reverse=False
    )


def lookup_type_in_mapping(mapping: typing.Dict[type, T], key: type) -> T:
    try:
        # _SpecialForm types like Literal, NoReturn don't have an __mro__ attribute
        bases = inspect.getmro(key)
    except AttributeError:
        raise KeyError("Special type {typ} not supported.".format(typ=key))

    for cls in bases:
        if cls in mapping:
            return mapping[cls]

    raise KeyError("Class '{cls}' not found in lookup.".format(cls=key))
