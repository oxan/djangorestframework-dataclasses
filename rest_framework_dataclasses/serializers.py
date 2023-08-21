from __future__ import annotations

import collections
import copy
import dataclasses
import datetime
import decimal
import uuid
from collections import OrderedDict
from enum import Enum
from typing import cast, Any, Dict, Generic, Iterable, List, Mapping, Optional, Tuple, Type, TypeVar

import rest_framework.fields
import rest_framework.serializers
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Model
from django.utils.functional import cached_property
from rest_framework.fields import empty
from rest_framework.relations import HyperlinkedRelatedField, PrimaryKeyRelatedField
from rest_framework.utils.field_mapping import get_relation_kwargs

from rest_framework_dataclasses import fields, field_utils, typing_utils
from rest_framework_dataclasses.field_utils import get_dataclass_definition, DataclassDefinition, TypeInfo
from rest_framework_dataclasses.types import Dataclass


# Define some types to make type hinting more readable
KWArgs = Dict[str, Any]
SerializerField = rest_framework.fields.Field
SerializerFieldDefinition = Tuple[Type[SerializerField], KWArgs]
T = TypeVar('T', bound=Dataclass)
AnyT = TypeVar('AnyT')


# Helper function create a dataclass instance
def _create_instance(dataclass_type: Type[T], fields_map: Dict[str, dataclasses.Field[Any]], values: KWArgs) -> T:
    # Aggregate fields by whether they must (or, at minimum can) be supplied to the constructor, or they can't be.
    init_params = {name: value for name, value in values.items() if fields_map[name].init}
    set_params = {name: value for name, value in values.items() if not fields_map[name].init}

    instance = dataclass_type(**init_params)
    for name, value in set_params.items():
        setattr(instance, name, value)
    return instance


# Helper function to strip the empty sentinel value and replace it with the default value from a dataclass
def _strip_empty_sentinels(data: AnyT, instance: Optional[AnyT] = None) -> AnyT:
    if dataclasses.is_dataclass(data) and not isinstance(data, type):
        values = {field.name: _strip_empty_sentinels(getattr(data, field.name),
                                                     getattr(instance, field.name, None))
                  for field in dataclasses.fields(data)
                  if getattr(data, field.name) is not empty}
        if instance:
            for field, value in values.items():
                setattr(instance, field, value)
            return instance
        else:
            return cast(AnyT, _create_instance(type(data), {f.name: f for f in dataclasses.fields(data)}, values))
    elif isinstance(data, list):
        return cast(AnyT, [_strip_empty_sentinels(item) for item in data])
    elif isinstance(data, dict):
        return cast(AnyT, {key: _strip_empty_sentinels(value) for key, value in data.items()})
    return data


# noinspection PyMethodMayBeStatic
class DataclassSerializer(rest_framework.serializers.Serializer, Generic[T]):
    """
    A `DataclassSerializer` is just a regular `Serializer`, except that:

    * A set of default fields are automatically populated.
    * A set of default validators are automatically populated.
    * Default `.create()` and `.update()` implementations are provided.

    The process of automatically determining a set of serializer fields based on the dataclass fields is slightly
    complex, but you almost certainly don't need to dig into the implementation.

    If the `DataclassSerializer` class *doesn't* generate the set of fields that you need you should either declare the
    extra/differing fields explicitly on the serializer class, or simply use a `Serializer` class.
    """

    # The mapping of field types to serializer fields
    serializer_field_mapping: Mapping[type, Type[SerializerField]] = {
        int:                rest_framework.fields.IntegerField,
        float:              rest_framework.fields.FloatField,
        bool:               rest_framework.fields.BooleanField,
        str:                rest_framework.fields.CharField,
        decimal.Decimal:    fields.DefaultDecimalField,
        datetime.date:      rest_framework.fields.DateField,
        datetime.datetime:  rest_framework.fields.DateTimeField,
        datetime.time:      rest_framework.fields.TimeField,
        datetime.timedelta: rest_framework.fields.DurationField,
        uuid.UUID:          rest_framework.fields.UUIDField,
        list:               fields.IterableField,
        dict:               fields.MappingField,
    }
    serializer_related_field: Type[SerializerField] = PrimaryKeyRelatedField
    serializer_union_field: Type[SerializerField] = fields.UnionField

    # Unfortunately this cannot be an actual field as Python processes the class before it defines the class, but this
    # comes close enough.
    @property
    def serializer_dataclass_field(self) -> Type[SerializerField]:
        return DataclassSerializer

    # Type hints for fields on the parent class
    _declared_fields: Dict[str, SerializerField]
    _validated_data: T

    # Type hints for fields
    dataclass: Type[T]

    # Override constructor to allow "anonymous" usage by passing the dataclass type and extra kwargs as a constructor
    # parameter instead of via a Meta class.
    def __init__(self, *args: Any, **kwargs: Any):
        self.dataclass = kwargs.pop('dataclass', None)
        self.extra_kwargs = kwargs.pop('extra_kwargs', None)
        super(DataclassSerializer, self).__init__(*args, **kwargs)

    @classmethod
    def many_init(cls, *args: Any, **kwargs: Any) -> DataclassListSerializer[T]:
        """
        Implements the creation of a `DataclassListSerializer` parent class when `many=True` is used.
        """
        allow_empty = kwargs.pop('allow_empty', None)

        list_kwargs = {key: value for key, value in kwargs.items()
                       if key in rest_framework.serializers.LIST_SERIALIZER_KWARGS}
        list_kwargs['child'] = cls(*args, **kwargs)

        if allow_empty is not None:
            list_kwargs['allow_empty'] = allow_empty

        meta = getattr(cls, 'Meta', None)
        list_serializer_class = getattr(meta, 'list_serializer_class', DataclassListSerializer)
        return list_serializer_class(*args, **list_kwargs)

    # Parse and validate the configuration to a more usable format

    @cached_property
    def dataclass_definition(self) -> DataclassDefinition[T]:
        # Determine the dataclass that we should operate on.
        if self.dataclass:
            assert not hasattr(self, 'Meta'), (
                "Class '{serializer_class}' may not have `Meta` attribute when instantiated with `dataclass` parameter."
                .format(serializer_class=self.__class__.__name__)
            )

            dataclass_type = self.dataclass
        else:
            assert hasattr(self, 'Meta'), (
                "Class '{serializer_class}' missing `Meta` attribute."
                .format(serializer_class=self.__class__.__name__)
            )

            meta = getattr(self, 'Meta')
            assert hasattr(meta, 'dataclass'), (
                "Class '{serializer_class}' missing `Meta.dataclass` attribute."
                .format(serializer_class=self.__class__.__name__)
            )

            dataclass_type = meta.dataclass

        # Make sure we're dealing with an actual dataclass.
        if not dataclasses.is_dataclass(dataclass_type):
            raise ValueError(
                "Class '{serializer_class}' can only be used to serialize dataclasses."
                .format(serializer_class=self.__class__.__name__)
            )

        # Cast back to Type[T], as mypy thinks it's a Type[DataclassInstance] due to the is_dataclass() check.
        # https://github.com/python/mypy/issues/14941
        return get_dataclass_definition(cast(Type[T], dataclass_type))

    # Default `create` and `update` behavior...

    def create(self, validated_data: T) -> T:
        if self.root.partial:
            return _strip_empty_sentinels(validated_data)
        return validated_data

    def update(self, instance: T, validated_data: T) -> T:
        if self.root.partial:
            return _strip_empty_sentinels(validated_data, instance)

        # Don't just return `validated_data` here, as the idea of update() is that it changes the existing object (which
        # might have references outside our control) instead of creating a new object.
        for field in self.dataclass_definition.fields.keys():
            setattr(instance, field, getattr(validated_data, field))
        return instance

    def save(self, **kwargs: KWArgs) -> T:
        assert hasattr(self, '_errors'), (
            "You must call `.is_valid()` before calling `.save()`."
        )

        assert not self.errors, (
            "You cannot call `.save()` on a serializer with invalid data."
        )

        assert not hasattr(self, '_data'), (
            "You cannot call `.save()` after accessing `serializer.data`."
            "If you need to access data before committing to the dataclass then "
            "inspect 'serializer.validated_data' instead. "
        )

        # Explicitly use the internal validated_data here, as the empty sentinel values must not be stripped yet. Do not
        # use dataclasses.replace(), as it doesn't handle non-init fields properly.
        obj = copy.deepcopy(self._validated_data)
        for field, value in kwargs.items():
            setattr(obj, field, value)

        if self.instance is not None:
            self.instance = self.update(self.instance, obj)
        else:
            self.instance = self.create(obj)

        assert self.instance is not None, (
            '`update()` or `create()` did not return an object instance.'
        )

        return self.instance

    # Determine the fields to apply...

    def get_fields(self) -> Dict[str, SerializerField]:
        """
        Return the dict of field names -> field instances that should be used for `self.fields` when instantiating the
        serializer.
        """
        # Copy declared fields, so that the field on the serializer class remains unchanged when the fields are bound to
        # the serializer instance.
        declared_fields = copy.deepcopy(self._declared_fields)

        # Copy fields declared in metadata, for the same reason.
        metadata_fields = {field.name: copy.deepcopy(field.metadata['serializer_field'])
                           for field in self.dataclass_definition.fields.values()
                           if 'serializer_field' in field.metadata}

        # Determine all fields that should be included on the serializer.
        field_names = self.get_field_names()

        # Determine any extra field arguments that should be included.
        extra_kwargs = self.get_extra_kwargs()

        # Determine the fields that should be included on the serializer.
        fields = OrderedDict()

        for field_name in field_names:
            # If the field is explicitly declared, either on the serializer or in the field metadata, then use that.
            if field_name in declared_fields or field_name in metadata_fields:
                assert field_name not in extra_kwargs, (
                    "Cannot both declare the field '{field_name}' and include it in '{serializer_class}' "
                    "`extra_kwargs` or `read_only_fields` option. Move all options to the field declaration."
                    .format(field_name=field_name, serializer_class=self.__class__.__name__)
                )

                # Prefer the field declared on the serializer above the one declared in field metadata.
                fields[field_name] = declared_fields.get(field_name, metadata_fields.get(field_name, None))
                continue

            extra_field_kwargs = extra_kwargs.get(field_name, {})
            fields[field_name] = self.create_field(field_name, extra_field_kwargs)

        return fields

    # Methods for determining the set of field names to include...

    def get_field_names(self) -> Iterable[str]:
        """
        Returns the list of all field names that should be created when instantiating this serializer class. This is
        based on the default set of fields, but also takes into account the `Meta.fields` or `Meta.exclude` options
        if they have been specified.
        """
        # Retrieve names of the declared fields.
        declared_field_names = self._declared_fields.keys()

        # Read configuration from Meta class.
        meta = getattr(self, 'Meta', None)
        fields = getattr(meta, 'fields', None)
        exclude = getattr(meta, 'exclude', None)

        if fields and fields != rest_framework.serializers.ALL_FIELDS and not isinstance(fields, (list, tuple)):
            raise TypeError(
                "The `fields` option must be a list or tuple or '__all__'. Got '{type}'."
                .format(type=type(fields).__name__)
            )

        if exclude and not isinstance(exclude, (list, tuple)):
            raise TypeError(
                "The `exclude` option must be a list or tuple. Got '{type}'."
                .format(type=type(exclude).__name__)
            )

        assert not (fields and exclude), (
            "Cannot set both `fields` and `exclude` options on serializer '{serializer_class}'."
            .format(serializer_class=self.__class__.__name__)
        )

        # If fields is not specified, or is the magic all fields option, make it a list consisting of the all fields
        # placeholder for now.
        if fields is None or fields == rest_framework.serializers.ALL_FIELDS:
            fields = [rest_framework.serializers.ALL_FIELDS]

        # For explicitly specified fields, ensure that they are valid.
        for field_name in fields:
            assert (
                field_name == rest_framework.serializers.ALL_FIELDS or                                        # all fields magic option
                field_name in self.dataclass_definition.fields or                                             # dataclass fields
                field_name in declared_field_names or                                                         # declared fields
                isinstance(getattr(self.dataclass_definition.dataclass_type, field_name, None), property) or  # property
                callable(getattr(self.dataclass_definition.dataclass_type, field_name, None))                 # methods
            ), (
                "The field '{field_name}' was included on serializer {serializer_class} in the `fields` option, "
                "but does not match any dataclass field."
                .format(field_name=field_name, serializer_class=self.__class__.__name__)
            )

        if rest_framework.serializers.ALL_FIELDS not in fields:
            # If there are only explicitly specified fields, ensure that all declared fields are included. Do not
            # require any fields that are declared in a parent class, in order to allow serializer subclasses to only
            # include a subset of fields.
            required_field_names = set(declared_field_names)
            for cls in self.__class__.__bases__:
                required_field_names -= set(getattr(cls, '_declared_fields', []))

            for field_name in required_field_names:
                assert field_name in fields, (
                    "The field '{field_name}' was declared on serializer '{serializer_class}', but has not been "
                    "included in the `fields` option."
                    .format(field_name=field_name, serializer_class=self.__class__.__name__)
                )
            return list(fields)

        # The field list now includes the magic all fields option, so replace it with the default field names.
        fields = list(fields)
        fields.remove(rest_framework.serializers.ALL_FIELDS)
        fields.extend(self.get_default_field_names(declared_field_names))

        if exclude is not None:
            # If `Meta.exclude` is included, then remove those fields.
            for field_name in exclude:
                assert field_name not in declared_field_names, (
                    "Cannot both declare the field '{field_name}' and include it in '{serializer_class}' `exclude` "
                    "option. Remove the field or, if inherited from a parent serializer, disable with "
                    "`{field_name} = None`."
                    .format(field_name=field_name, serializer_class=self.__class__.__name__)
                )

                assert field_name in fields, (
                    "The field '{field_name}' was included on serializer {serializer_class} in the `exclude` option, "
                    "but does not match any dataclass field."
                    .format(field_name=field_name, serializer_class=self.__class__.__name__)
                )

                fields.remove(field_name)

        return fields

    def get_default_field_names(self, declared_fields: Iterable[str]) -> Iterable[str]:
        """
        Return the default list of field names that will be used if the `Meta.fields` option is not specified.
        """
        return (
            list(declared_fields) +
            list(self.dataclass_definition.fields)
        )

    # Methods for constructing serializer fields...

    def create_field(self, field_name: str, extra_kwargs: KWArgs) -> SerializerField:
        # Get the source field (this can be useful to represent a single dataclass field in multiple ways in the
        # serialization state).
        source = extra_kwargs.get('source', '*')
        if source == '*':
            source = field_name

        # Determine the serializer field class and keyword arguments.
        if source in self.dataclass_definition.fields:
            field = self.dataclass_definition.fields[source]
            if 'serializer_kwargs' in field.metadata:  # merge extra kwargs defined in the field metadata
                extra_kwargs = {**field.metadata['serializer_kwargs'], **extra_kwargs}

            type_info = field_utils.get_type_info(self.dataclass_definition.field_types[source])
            field_class, field_kwargs = self.build_typed_field(source, type_info, extra_kwargs)
        elif hasattr(self.dataclass_definition.dataclass_type, source):
            field_class, field_kwargs = self.build_property_field(source)
        else:
            field_class, field_kwargs = self.build_unknown_field(source)

        # Include any extra kwargs defined through `Meta.extra_kwargs`
        field_kwargs = self.include_extra_kwargs(field_kwargs, extra_kwargs)

        # Create the serializer field instance.
        return field_class(**field_kwargs)

    def build_typed_field(self, field_name: str, type_info: TypeInfo,
                          extra_kwargs: KWArgs) -> SerializerFieldDefinition:
        """
        Create a serializer field for a typed dataclass field.
        """
        if type_info.is_mapping or type_info.is_many:
            field_class, field_kwargs = self.build_composite_field(field_name, type_info, extra_kwargs)
        elif dataclasses.is_dataclass(type_info.base_type):
            field_class, field_kwargs = self.build_dataclass_field(field_name, type_info)
        elif isinstance(type_info.base_type, type) and issubclass(type_info.base_type, Model):
            field_class, field_kwargs = self.build_relational_field(field_name, type_info)
        elif typing_utils.is_union_type(type_info.base_type):
            field_class, field_kwargs = self.build_union_field(field_name, type_info, extra_kwargs)
        elif isinstance(type_info.base_type, type) and issubclass(type_info.base_type, Enum):
            field_class, field_kwargs = self.build_enum_field(field_name, type_info)
        elif typing_utils.is_literal_type(type_info.base_type):
            field_class, field_kwargs = self.build_literal_field(field_name, type_info)
        else:
            field_class, field_kwargs = self.build_standard_field(field_name, type_info)

        # Mark a field as not-required if it has a default value (factory) on the dataclass. This is consistent with the
        # constructor of dataclasses, where these fields are also made optional. Note that this is different from the
        # `typing.Optional[]` qualifier, which merely makes the field nullable, but still requires it to be passed. Of
        # course it makes sense for `Optional` fields to have `None` as a default value, but that's up to the user.
        field = self.dataclass_definition.fields[field_name]
        if field.default is not dataclasses.MISSING or field.default_factory is not dataclasses.MISSING:
            field_kwargs['required'] = False

            # Explicitly don't set the default argument here. Setting it would cause the default value to be inserted in
            # the native representation (`to_internal_value()` argument) if the field wasn't supplied by the user (for
            # non-partial updates). This in turn would cause `update()` to overwrite non-supplied fields with the
            # defaults, which is undesirable. Instead, let the dataclass constructor apply the default values when the
            # dataclass is instantiated.

        # Mark a field as nullable if it is declared as Optional[] (which has a confusing name).
        if type_info.is_nullable:
            field_kwargs['allow_null'] = True

        # The final qualifier declares that a variable or attribute should not be reassigned (PEP 591). Mark the field
        # as read only.
        if type_info.is_final:
            field_kwargs['read_only'] = True

        return field_class, field_kwargs

    def build_composite_field(self, field_name: str, type_info: TypeInfo,
                              extra_kwargs: KWArgs) -> SerializerFieldDefinition:
        """
        Create a composite (mapping or list) field.
        """
        # Default to using the field for a dict or list from the field mapping, so that it can easily be changed without
        # overriding this method.
        if type_info.is_mapping:
            field_class = self.serializer_field_mapping[dict]
        else:
            field_class = self.serializer_field_mapping[list]
        field_kwargs: KWArgs = {}

        # If the type of the container is known, see if there's a field override; and pass it to the field.
        if type_info.container_type:
            field_kwargs['container'] = type_info.container_type
            try:
                field_class = field_utils.lookup_type_in_mapping(self.serializer_field_mapping, type_info.container_type)
            except KeyError:
                pass

        # If the base type is not specified or is any type, no need to bother creating the child field.
        if type_info.base_type is Any:
            return field_class, field_kwargs

        # Recurse to build the child field (i.e. the field of every instance). We pass the extra kwargs that are
        # specified for the child field through, so these can be used to recursively specify kwargs for child fields.
        extra_child_field_kwargs = extra_kwargs.get('child_kwargs', {})
        base_type_info = field_utils.get_type_info(type_info.base_type)
        child_field_class, child_field_kwargs = self.build_typed_field(field_name, base_type_info,
                                                                       extra_child_field_kwargs)

        # Include the extra kwargs specified for the child field before instantiating it.
        child_field_kwargs = self.include_extra_kwargs(child_field_kwargs, extra_child_field_kwargs)

        # Create child field and initialize parent field kwargs
        child_field = child_field_class(**child_field_kwargs)
        field_kwargs['child'] = child_field
        return field_class, field_kwargs

    def build_standard_field(self, field_name: str, type_info: TypeInfo) -> SerializerFieldDefinition:
        """
        Create regular dataclass fields.
        """
        try:
            field_class = field_utils.lookup_type_in_mapping(self.serializer_field_mapping, type_info.base_type)
            field_kwargs: KWArgs = {}

            return field_class, field_kwargs
        except KeyError:
            # When resolving the type hint fails, raise a nice descriptive error based on the outermost type of the
            # field (this makes solving deep recursive errors much easier).
            field_type = self.dataclass_definition.field_types[field_name]
            raise NotImplementedError(
                "Automatic serializer field deduction not supported for field '{field}' on '{dataclass}' "
                "of type '{type}' (during search for field of type '{reduced_type}')."
                .format(dataclass=self.dataclass_definition.dataclass_type.__name__, field=field_name,
                        type=field_type, reduced_type=type_info.base_type)
            )

    def build_relational_field(self, field_name: str, type_info: TypeInfo) -> SerializerFieldDefinition:
        """
        Create fields for models.
        """
        relation_info = field_utils.get_relation_info(type_info)
        field_class = self.serializer_related_field
        field_kwargs = get_relation_kwargs(field_name, relation_info)

        # `view_name` is only valid for hyperlinked relationships.
        if not issubclass(field_class, HyperlinkedRelatedField):
            field_kwargs.pop('view_name', None)

        return field_class, field_kwargs

    def build_union_field(self, field_name: str, type_info: TypeInfo,
                          extra_kwargs: KWArgs) -> SerializerFieldDefinition:
        """
        Create UnionField from a union type.
        """
        # Pass the extra kwargs that are specified for the child field through to *all* child serializers.
        extra_child_kwargs = extra_kwargs.get('child_kwargs', {})

        child_fields = {}
        for member_type in typing_utils.get_union_choices(type_info.base_type):
            member_type_info = field_utils.get_type_info(member_type)
            child_field_class, child_kwargs = self.build_typed_field(field_name, member_type_info, extra_child_kwargs)
            child_field_kwargs = self.include_extra_kwargs(child_kwargs, extra_child_kwargs)
            child_fields[member_type_info.base_type] = child_field_class(**child_field_kwargs)

        field_class = self.serializer_union_field
        field_kwargs = {
            'child_fields': child_fields
        }
        return field_class, field_kwargs

    def build_enum_field(self, field_name: str, type_info: TypeInfo) -> SerializerFieldDefinition:
        """
        Create EnumField from a Enum type.
        """
        field_class = fields.EnumField
        field_kwargs = {
            'enum_class': type_info.base_type
        }
        return field_class, field_kwargs

    # noinspection PyUnusedLocal
    def build_literal_field(self, field_name: str, type_info: TypeInfo) -> SerializerFieldDefinition:
        """
        Create ChoiceField from a Literal[...] type.
        """
        field_class = rest_framework.fields.ChoiceField
        choices = typing_utils.get_literal_choices(type_info.base_type)
        field_kwargs = {
            'choices': [val for val in choices if val not in (None, '')],
            'allow_blank': '' in choices,
        }

        return field_class, field_kwargs

    def build_dataclass_field(self, field_name: str, type_info: TypeInfo) -> SerializerFieldDefinition:
        """
        Create fields for dataclasses.
        """
        try:
            field_class = field_utils.lookup_type_in_mapping(self.serializer_field_mapping, type_info.base_type)
        except KeyError:
            field_class = self.serializer_dataclass_field

        # allow user to map a dataclass to a regular serializer Field class
        if not issubclass(field_class, DataclassSerializer):
            return self.build_standard_field(field_name, type_info)

        field_kwargs = {'dataclass': type_info.base_type,
                        'many': type_info.is_many}

        return field_class, field_kwargs

    # noinspection PyUnusedLocal
    def build_property_field(self, field_name: str) -> SerializerFieldDefinition:
        """
        Create a read only field for dataclass methods and properties.
        """
        field_class = rest_framework.fields.ReadOnlyField
        field_kwargs: KWArgs = {}

        return field_class, field_kwargs

    def build_unknown_field(self, field_name: str) -> SerializerFieldDefinition:
        """
        Raise an error on any unknown fields.
        """
        raise ImproperlyConfigured(
            "Field name '{field_name}' is not valid for dataclass '{class_name}'."
            .format(field_name=field_name, class_name=self.dataclass_definition.dataclass_type.__name__)
        )

    # Methods for determining additional keyword arguments to apply...

    def include_extra_kwargs(self, kwargs: KWArgs, extra_kwargs: KWArgs) -> KWArgs:
        """
        Include any `extra_kwargs` that have been included for this field, possibly removing any incompatible existing
        keyword arguments.
        """
        # If the field is made read only, drop write-only related arguments.
        if extra_kwargs.get('read_only', False):
            for attr in [
                'required', 'default', 'allow_blank', 'allow_null',
                'min_length', 'max_length', 'min_value', 'max_value',
                'validators', 'queryset'
            ]:
                kwargs.pop(attr, None)

        # If `default` is specified, `required` may not be specified. If the field is not explicitly specified as not
        # required (the behaviour of `default`), remove that specification.
        if extra_kwargs.get('default') and kwargs.get('required') is False:
            kwargs.pop('required')

        if extra_kwargs.get('read_only', kwargs.get('read_only', False)):
            extra_kwargs.pop('required', None)  # Read only fields should always omit the 'required' argument.

        if 'child_kwargs' in extra_kwargs:
            extra_kwargs.pop('child_kwargs', None)  # Always drop the child_kwargs field, as it's applied manually

        kwargs.update(extra_kwargs)

        return kwargs

    def get_extra_kwargs(self) -> KWArgs:
        """
        Return a dictionary mapping field names to a dictionary of additional keyword arguments.
        """
        meta = getattr(self, 'Meta', None)
        extra_kwargs = copy.deepcopy(getattr(meta, 'extra_kwargs', None)) if meta is not None else None
        if extra_kwargs is None:
            extra_kwargs = self.extra_kwargs or {}

        read_only_fields = getattr(meta, 'read_only_fields', None)
        if read_only_fields is not None:
            if not isinstance(read_only_fields, (list, tuple)):
                raise TypeError(
                    "The `read_only_fields` option must be a list or tuple. Got '{type}'."
                    .format(type=type(read_only_fields).__name__)
                )

            for field_name in read_only_fields:
                kwargs = extra_kwargs.get(field_name, {})
                kwargs['read_only'] = True
                extra_kwargs[field_name] = kwargs
        else:
            # Guard against the possible misspelling `readonly_fields` (used by the Django admin and others).
            assert not hasattr(meta, 'readonly_fields'), (
                "Serializer '{serializer_class}' has field `readonly_fields`; the correct spelling for the option is "
                "`read_only_fields`."
                .format(serializer_class=self.__class__.__name__)
            )

        return extra_kwargs

    # Methods to convert between internal normalized value and serialized representation.

    def to_internal_value(self, data: Dict[str, Any]) -> T:
        """
        Convert a dictionary representation of the dataclass containing only primitive values to a dataclass instance.
        """
        native_values = super(DataclassSerializer, self).to_internal_value(data)

        # If the source is a wildcard, don't try to instantiate anything, but just return the native values as a dict.
        # It'll be merged into the native values of the parent serializer by the parent class.
        if self.source == '*':
            return native_values

        # If any fields have a wildcard source, their native value will hold a values dictionary instead of a dataclass,
        # so convert them into a dataclass.
        if any(field.source == '*' for field in self.fields.values()):
            for field_name, tp in self.dataclass_definition.field_types.items():
                if (
                    field_name in native_values and
                    dataclasses.is_dataclass(tp) and
                    isinstance(native_values[field_name], collections.abc.Mapping)
                ):
                    dataclass_fields = {field.name: field for field in dataclasses.fields(tp)}
                    native_values[field_name] = _create_instance(tp, dataclass_fields, native_values[field_name])

        # Only insert empty sentinel value for non-supplied values when the root serializer is in partial mode, to
        # prevent them from showing up otherwise.
        if self.root.partial:
            native_values.update({key: empty
                                  for key, field in self.dataclass_definition.fields.items()
                                  if key not in native_values and field.init})

        return _create_instance(self.dataclass_definition.dataclass_type,
                                self.dataclass_definition.fields,
                                native_values)

    @cached_property
    def validated_data(self) -> T:
        """
        Replace empty sentinel value with default value in public representation. Note that this doesn't work for
        partial updates.
        """
        internal_validated_data = super(DataclassSerializer, self).validated_data
        if self.root.partial:
            return _strip_empty_sentinels(internal_validated_data)
        return internal_validated_data


class DataclassListSerializer(rest_framework.serializers.ListSerializer, Generic[T]):
    # Type hints for (private) fields on the parent class
    _validated_data: List[T]

    def save(self, **kwargs: KWArgs) -> T:
        assert hasattr(self, '_errors'), (
            "You must call `.is_valid()` before calling `.save()`."
        )

        assert not self.errors, (
            "You cannot call `.save()` on a serializer with invalid data."
        )

        assert not hasattr(self, '_data'), (
            "You cannot call `.save()` after accessing `serializer.data`."
            "If you need to access data before committing to the dataclass then "
            "inspect 'serializer.validated_data' instead. "
        )

        # Explicitly use the internal validated_data here, as the empty sentinel values must not be stripped yet. Do not
        # use dataclasses.replace(), as it doesn't handle non-init fields properly.
        validated_data = []
        for item in self._validated_data:
            obj = copy.deepcopy(item)
            for field, value in kwargs.items():
                setattr(obj, field, value)
            validated_data.append(obj)

        if self.instance is not None:
            self.instance = self.update(self.instance, validated_data)
        else:
            self.instance = self.create(validated_data)

        assert self.instance is not None, (
            '`update()` or `create()` did not return an object instance.'
        )

        return self.instance

    @cached_property
    def validated_data(self) -> List[T]:
        """
        Replace empty sentinel value with default value in public representation.
        """
        internal_validated_data = super(DataclassListSerializer, self).validated_data
        if self.root.partial:
            return _strip_empty_sentinels(internal_validated_data)
        return internal_validated_data


class HyperlinkedDataclassSerializer(DataclassSerializer, Generic[T]):
    serializer_related_field = HyperlinkedRelatedField

    @property
    def serializer_dataclass_field(self) -> Type[SerializerField]:
        return HyperlinkedDataclassSerializer
