import collections.abc
from typing import Any, Dict, Generic, Type, TypeVar, Union, Optional

from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import ValidationError
from rest_framework.fields import Field, ChoiceField, DecimalField, DictField, ListField
from rest_framework_dataclasses import field_utils

T = TypeVar('T')


class DefaultDecimalField(DecimalField):
    def __init__(self, **kwargs):
        if 'max_digits' not in kwargs:
            kwargs['max_digits'] = None
        if 'decimal_places' not in kwargs:
            # Maybe this should be configurable, but it doesn't seem that useful. File an issue if you want it to.
            kwargs['decimal_places'] = 2

        super(DefaultDecimalField, self).__init__(**kwargs)


class EnumField(ChoiceField):
    def __init__(self, enum_class, by_name=False, **kwargs):
        self.enum_class = enum_class
        self.by_name = by_name
        if 'choices' not in kwargs:
            kwargs['choices'] = [(self.to_representation(member), member.name) for member in self.enum_class]

        super(EnumField, self).__init__(**kwargs)

    def to_internal_value(self, data):
        try:
            if self.by_name:
                return self.enum_class[data]
            else:
                return self.enum_class(data)
        except (KeyError, ValueError):
            self.fail('invalid_choice', input=data)

    def to_representation(self, value):
        # Some external libraries expect to be able to call to_representation() with the key from the choices
        # array, which seems at least somewhat reasonable. See #40.
        if not isinstance(value, self.enum_class):
            if value in self.choices:
                return value
            self.fail('invalid_choice', input=value)

        if self.by_name:
            return value.name
        else:
            return value.value


class IterableField(ListField):
    def __init__(self, **kwargs):
        self.container = kwargs.pop('container', list)
        super(IterableField, self).__init__(**kwargs)

    def to_internal_value(self, value):
        return self.container(super(IterableField, self).to_internal_value(value))


class MappingField(DictField):
    def __init__(self, **kwargs):
        self.container = kwargs.pop('container', dict)
        super(MappingField, self).__init__(**kwargs)

    def to_internal_value(self, value):
        return self.container(super(MappingField, self).to_internal_value(value))


class UnionField(Field, Generic[T]):
    # Name of the field with the tag that identifies which of the member types is contained in the field.
    discriminator_field_name = 'type'
    # Name for `nest_value` fields.
    value_field_name = 'value'

    child_fields: Dict[str, Field]
    type_mapping: Dict[type, str]

    def __init__(self,
                 child_fields: Dict[type, Union[Field, Type[Field]]],
                 *,
                 nest_value: bool = False,
                 discriminator_field_name: Optional[str] = None,
                 value_field_name: Optional[str] = None,
                 **kwargs: Any):
        super().__init__(**kwargs)
        self.nest_value = nest_value
        if discriminator_field_name is not None:
            self.discriminator_field_name = discriminator_field_name
        if value_field_name is not None:
            self.value_field_name = value_field_name

        self.child_fields = {}
        self.type_mapping = {}
        for tp, field in child_fields.items():
            discriminator = self.get_discriminator(tp)
            if isinstance(field, type):
                field = field()
            self.child_fields[discriminator] = field
            self.type_mapping[tp] = discriminator

    def get_discriminator(self, tp: type) -> str:
        return tp.__name__

    def to_representation(self, data: T) -> Dict[str, Any]:
        discriminator = field_utils.lookup_type_in_mapping(self.type_mapping, type(data))
        field = self.child_fields[discriminator]

        ret = field.to_representation(data)
        if self.nest_value:
            ret = {self.value_field_name: ret}
        elif not isinstance(ret, collections.abc.Mapping):
            raise ImproperlyConfigured(
                'Representation for `{type}` value of `{serializer}.{field}` is not a mapping, which prohibits '
                'insertion of discriminator field. Either enable `nest_value` on the `UnionField`, or change the '
                '`{type}` field to one that returns a mapping.'.format(
                    type=type(data).__name__,
                    serializer=self.parent.__class__.__name__,
                    field=self.field_name,
                )
            )

        ret[self.discriminator_field_name] = discriminator
        return ret

    def to_internal_value(self, data: Dict[str, Any]) -> T:
        if self.discriminator_field_name not in data:
            raise ValidationError({self.discriminator_field_name: 'Discriminator field must be present.'})
        discriminator = data[self.discriminator_field_name]
        if discriminator not in self.child_fields:
            raise ValidationError({self.discriminator_field_name: 'Not a valid type.'})
        field = self.child_fields[discriminator]

        if self.nest_value:
            if self.value_field_name not in data:
                raise ValidationError({self.value_field_name: 'This field is required.'})
            data = data[self.value_field_name]

        return field.to_internal_value(data)
