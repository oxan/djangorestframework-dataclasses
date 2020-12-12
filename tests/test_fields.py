import dataclasses
import datetime
import decimal
import enum
import re
import sys
import typing
import unittest
import uuid
from collections import abc

import django
from django.db import models
from rest_framework import fields, relations

from rest_framework_dataclasses import field_utils, fields as custom_fields
from rest_framework_dataclasses.serializers import DataclassSerializer
from rest_framework_dataclasses.types import Final, Literal


class FieldsTest(unittest.TestCase):
    def build_typed_field(self, type_hint, extra_kwargs=None):
        testclass = dataclasses.make_dataclass('TestDataclass', [('test_field', type_hint)])
        serializer = DataclassSerializer(dataclass=testclass)
        type_info = field_utils.get_type_info(serializer.dataclass_definition.field_types['test_field'])

        extra_kwargs = extra_kwargs or {}
        return serializer.build_typed_field('test_field', type_info, extra_kwargs)

    def check_field(self, type_hint, field, kwargs=None):
        field_class, field_kwargs = self.build_typed_field(type_hint)
        self.assertTrue(issubclass(field_class, field), f'for field of type {type_hint}')

        if kwargs is not None:
            self.assertDictEqual(field_kwargs, kwargs, f'arguments for field of type {type_hint}')

    def test_composite(self):
        var_type = typing.TypeVar('var_type')

        self.check_field(typing.Iterable[str], fields.ListField)
        self.check_field(typing.Sequence[str], fields.ListField)
        self.check_field(typing.Tuple[str], fields.ListField)
        self.check_field(typing.List[str], fields.ListField)
        self.check_field(typing.List[typing.Any], fields.ListField, {})
        self.check_field(typing.List[var_type], fields.ListField, {})
        self.check_field(typing.List, fields.ListField, {})
        self.check_field(list, fields.ListField, {})

        self.check_field(typing.Mapping[str, int], fields.DictField)
        self.check_field(typing.Dict[str, int], fields.DictField)
        self.check_field(typing.Dict[str, typing.Any], fields.DictField, {})
        self.check_field(typing.Dict[str, var_type], fields.DictField, {})
        self.check_field(typing.Dict, fields.DictField, {})
        self.check_field(dict, fields.DictField, {})

        self.check_field(typing.Optional[typing.List[str]], fields.ListField)
        self.check_field(typing.Optional[typing.Dict[str, int]], fields.DictField)

        # check that kwargs generated for the child field are actually applied
        _, list_kwargs = self.build_typed_field(typing.List[typing.Optional[str]])
        self.assertIsInstance(list_kwargs['child'], fields.CharField)
        self.assertFalse(list_kwargs['child'].required)
        self.assertTrue(list_kwargs['child'].allow_null)

        _, dict_kwargs = self.build_typed_field(typing.Dict[str, Literal['a', 'b', '']])
        self.assertIsInstance(dict_kwargs['child'], fields.ChoiceField)
        self.assertDictEqual(dict_kwargs['child'].choices, {'a': 'a', 'b': 'b'})
        self.assertTrue(dict_kwargs['child'].allow_blank)

        # check that child_kwargs are applied
        _, list_kwargs = self.build_typed_field(typing.List[int],
                                                extra_kwargs={'child_kwargs': {'max_value': 5}})
        self.assertIsInstance(list_kwargs['child'], fields.IntegerField)
        self.assertEqual(list_kwargs['child'].max_value, 5)

    @unittest.skipIf(sys.version_info < (3, 9, 0), 'Python 3.9 required')
    def test_composite_pep585(self):
        self.check_field(abc.Iterable[str], fields.ListField)
        self.check_field(abc.Sequence[str], fields.ListField)
        self.check_field(tuple[str], fields.ListField)
        self.check_field(list[str], fields.ListField)
        self.check_field(list[typing.Any], fields.ListField, {})

        self.check_field(abc.Mapping[str, int], fields.DictField)
        self.check_field(dict[str, int], fields.DictField)
        self.check_field(dict[str, typing.Any], fields.DictField, {})

        # check that kwargs generated for the child field are actually applied
        _, list_kwargs = self.build_typed_field(list[typing.Optional[str]])
        self.assertIsInstance(list_kwargs['child'], fields.CharField)
        self.assertFalse(list_kwargs['child'].required)
        self.assertTrue(list_kwargs['child'].allow_null)

        _, dict_kwargs = self.build_typed_field(dict[str, Literal['a', 'b', '']])
        self.assertIsInstance(dict_kwargs['child'], fields.ChoiceField)
        self.assertDictEqual(dict_kwargs['child'].choices, {'a': 'a', 'b': 'b'})
        self.assertTrue(dict_kwargs['child'].allow_blank)

    def test_nested(self):
        refclass = dataclasses.make_dataclass('ReferencedDataclass', [])
        self.check_field(refclass, DataclassSerializer,
                         {'dataclass': refclass, 'many': False})
        self.check_field(typing.Optional[refclass], DataclassSerializer,
                         {'dataclass': refclass, 'many': False, 'required': False, 'allow_null': True})

        # customizing the dataclass serializer by changing the serializer_dataclass_field property
        subclassed_serializer = type('SubclassedDataclassSerializer1', (DataclassSerializer, ), {})
        setattr(DataclassSerializer, 'serializer_dataclass_field', subclassed_serializer)
        self.check_field(refclass, subclassed_serializer, {'dataclass': refclass, 'many': False})

        # customizing the dataclass serializer by putting the type into the field mapping
        subclassed_serializer = type('SubclassedDataclassSerializer2', (DataclassSerializer, ), {})
        DataclassSerializer.serializer_field_mapping[refclass] = subclassed_serializer
        self.check_field(refclass, subclassed_serializer, {'dataclass': refclass, 'many': False})

    def test_relational(self):
        django.setup()

        class Person(models.Model):
            name = models.CharField(max_length=30)

            class Meta:
                app_label = 'tests'

        self.check_field(Person, relations.PrimaryKeyRelatedField,
                         {'queryset': Person._default_manager})
        self.check_field(typing.Optional[Person], relations.PrimaryKeyRelatedField,
                         {'queryset': Person._default_manager, 'required': False, 'allow_null': True})

    def test_literal(self):
        self.check_field(Literal['a', 'b'], fields.ChoiceField,
                         {'choices': ['a', 'b'], 'allow_blank': False})
        self.check_field(Literal['a', 'b', ''], fields.ChoiceField,
                         {'choices': ['a', 'b'], 'allow_blank': True})
        self.check_field(Literal['a', 'b', None], fields.ChoiceField,
                         {'choices': ['a', 'b'], 'allow_blank': False, 'required': False, 'allow_null': True})
        self.check_field(typing.Optional[Literal['a', 'b']], fields.ChoiceField,
                         {'choices': ['a', 'b'], 'allow_blank': False, 'required': False, 'allow_null': True})
        self.check_field(Literal['a', 'b', '', None], fields.ChoiceField,
                         {'choices': ['a', 'b'], 'allow_blank': True, 'required': False, 'allow_null': True})

    def test_enum(self):
        class Color(enum.Enum):
            RED = enum.auto()
            GREEN = enum.auto()
            BLUE = enum.auto()

        self.check_field(Color, custom_fields.EnumField, {'enum_class': Color})

    def test_standard_primitives(self):
        self.check_field(int, fields.IntegerField)
        self.check_field(float, fields.FloatField)
        self.check_field(bool, fields.BooleanField)
        self.check_field(str, fields.CharField)

        # Check that optional sets exactly required and allow_null (#16).
        self.check_field(typing.Optional[int], fields.IntegerField,
                         {'required': False, 'allow_null': True})
        self.check_field(typing.Optional[str], fields.CharField,
                         {'required': False, 'allow_null': True})

    def test_standard_final(self):
        self.check_field(Final[int], fields.IntegerField, {'read_only': True})
        self.check_field(Final[str], fields.CharField, {'read_only': True})

        # Final fields without an explicit type are not supported if the default value is not known. The case with a
        # default value is tested in create_field().
        with self.assertRaises(NotImplementedError):
            self.check_field(Final, fields.CharField, {'read_only': True})

    def test_standard_variable(self):
        var_str = typing.TypeVar('var_str', bound=str)
        var_any = typing.TypeVar('var_any')

        self.check_field(var_str, fields.CharField)

        with self.assertRaises(NotImplementedError):
            self.build_typed_field(var_any)

    def test_standard_decimal(self):
        self.check_field(decimal.Decimal, fields.DecimalField)

    def test_standard_dates(self):
        self.check_field(datetime.date, fields.DateField)
        self.check_field(datetime.datetime, fields.DateTimeField)
        self.check_field(datetime.time, fields.TimeField)
        self.check_field(datetime.timedelta, fields.DurationField)

    def test_standard_uuid(self):
        self.check_field(uuid.UUID, fields.UUIDField)

    def test_standard_subclass(self):
        custom_str = type('custom_str', (str, ), {})
        custom_date = type('custom_date', (datetime.date, ), {})
        self.check_field(custom_str, fields.CharField)
        self.check_field(custom_date, fields.DateField)

    def test_standard_error(self):
        msg = ("Automatic serializer field deduction not supported for field 'test_field' on 'TestDataclass' "
               "of type '<class 'complex'>' (during search for field of type '<class 'complex'>').")
        with self.assertRaisesRegex(NotImplementedError, re.escape(msg)):
            self.build_typed_field(complex)

        # Check _SpecialForm types that don't have an __mro__attribute (#6)
        msg = ("Automatic serializer field deduction not supported for field 'test_field' on 'TestDataclass' "
               "of type 'typing.Any' (during search for field of type 'None').")
        with self.assertRaisesRegex(NotImplementedError, re.escape(msg)):
            self.build_typed_field(typing.Any)
