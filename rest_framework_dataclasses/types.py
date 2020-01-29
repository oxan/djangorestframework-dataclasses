"""Type aliases/definitions for type checkers"""
from typing import TYPE_CHECKING, Type, Union, List, Tuple, Any, Dict

import rest_framework.fields


# Define some types to make type hinting more readable
KWArgs = Dict[str, Any]
SerializerField = rest_framework.fields.Field
SerializerFieldDefinition = Tuple[Type[SerializerField], KWArgs]
FieldsType = Union[List[str], Tuple[str]]

try:
    # Python 3.8 and later
    from typing import Final, Literal, Protocol
except ImportError:
    from typing_extensions import Final, Literal, Protocol


# Note that this doesn't actually work yet (https://stackoverflow.com/a/55240861)
class Dataclass(Protocol):
    __dataclass_fields__: Dict


if TYPE_CHECKING:
    FieldsOrAllType = Union[FieldsType, Literal['__all__']]

    class _MetaProtocol(Protocol):
        """
        Type annotation for Serializer `Meta` attribute. `Protocol` indicates that it's a duck type, not parent class.
        """
        dataclass: type
        fields: FieldsOrAllType
        exclude: FieldsType
        read_only_fields: FieldsType

    Metaclass = Type[_MetaProtocol]

else:
    # FIXME: drop if?
    # Fallback for Python 3.7, does not support Protocol, Literal
    FieldsOrAllType = Union[FieldsType, str]
    Metaclass = type
