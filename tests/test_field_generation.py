import collections
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
    def build_typed_field(self, type_hint, field=None, extra_kwargs=None):
        field_tuple = ('test_field', type_hint, field) if field else ('test_field', type_hint)
        testclass = dataclasses.make_dataclass('TestDataclass', [field_tuple])
        serializer = DataclassSerializer(dataclass=testclass)
        type_info = field_utils.get_type_info(serializer.dataclass_definition.field_types['test_field'])

        extra_kwargs = extra_kwargs or {}
        return serializer.build_typed_field('test_field', type_info, extra_kwargs)

    def check_field_additional(self, type_hint, field, serializer_field, serializer_kwargs=None):
        field_class, field_kwargs = self.build_typed_field(type_hint, field)
        self.assertEqual(field_class, serializer_field)

        if serializer_kwargs is not None:
            if 'child' in field_kwargs:
                field_kwargs['child'] = type(field_kwargs['child'])
            self.assertDictEqual(field_kwargs, serializer_kwargs, f'arguments for field of type {type_hint}')

    def check_field(self, type_hint, field, kwargs=None):
        self.check_field_additional(type_hint, None, field, kwargs)

    def test_arguments(self):
        # Check that no qualifiers emit no arguments.
        self.check_field_additional(int, None, fields.IntegerField, {})

        # Check that a default value (factory) sets required to False (#16, #38).
        self.check_field_additional(int, dataclasses.field(default=1), fields.IntegerField, {'required': False})
        self.check_field_additional(int, dataclasses.field(default_factory=1), fields.IntegerField, {'required': False})

        # Check that Optional sets allow_null to True (#16, #38).
        self.check_field_additional(typing.Optional[int], None, fields.IntegerField, {'allow_null': True})

        # Check that Final sets exactly read_only.
        self.check_field(Final[int], fields.IntegerField, {'read_only': True})

    def test_composite(self):
        var_type = typing.TypeVar('var_type')

        self.check_field(typing.Iterable[str], custom_fields.IterableField, {'child': fields.CharField})
        self.check_field(typing.Sequence[str], custom_fields.IterableField, {'child': fields.CharField})
        self.check_field(typing.Tuple[str], custom_fields.IterableField,
                         {'child': fields.CharField, 'container': tuple})
        self.check_field(typing.Set[str], custom_fields.IterableField, {'child': fields.CharField, 'container': set})
        self.check_field(typing.List[str], custom_fields.IterableField, {'child': fields.CharField, 'container': list})
        self.check_field(typing.List[typing.Any], custom_fields.IterableField, {'container': list})
        self.check_field(typing.List[var_type], custom_fields.IterableField, {'container': list})
        self.check_field(typing.List, custom_fields.IterableField, {'container': list})
        self.check_field(list, custom_fields.IterableField, {})

        self.check_field(typing.Mapping[str, int], custom_fields.MappingField, {'child': fields.IntegerField})
        self.check_field(typing.OrderedDict[str, int], custom_fields.MappingField,
                         {'child': fields.IntegerField, 'container': collections.OrderedDict})
        self.check_field(typing.Dict[str, int], custom_fields.MappingField,
                         {'child': fields.IntegerField, 'container': dict})
        self.check_field(typing.Dict[str, typing.Any], custom_fields.MappingField, {'container': dict})
        self.check_field(typing.Dict[str, var_type], custom_fields.MappingField, {'container': dict})
        self.check_field(typing.Dict, custom_fields.MappingField, {'container': dict})
        self.check_field(dict, custom_fields.MappingField, {})

        self.check_field(typing.Optional[typing.List[str]], custom_fields.IterableField,
                         {'allow_null': True, 'child': fields.CharField, 'container': list})
        self.check_field(typing.Optional[typing.Dict[str, int]], custom_fields.MappingField,
                         {'allow_null': True, 'child': fields.IntegerField, 'container': dict})

        # check that kwargs generated for the child field are actually applied
        _, list_kwargs = self.build_typed_field(typing.List[typing.Optional[str]])
        self.assertIsInstance(list_kwargs['child'], fields.CharField)
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
        self.check_field(abc.Iterable[str], custom_fields.IterableField, {'child': fields.CharField})
        self.check_field(abc.Sequence[str], custom_fields.IterableField, {'child': fields.CharField})
        self.check_field(tuple[str], custom_fields.IterableField, {'child': fields.CharField, 'container': tuple})
        self.check_field(set[str], custom_fields.IterableField, {'child': fields.CharField, 'container': set})
        self.check_field(list[str], custom_fields.IterableField, {'child': fields.CharField, 'container': list})
        self.check_field(list[typing.Any], custom_fields.IterableField, {'container': list})

        self.check_field(abc.Mapping[str, int], custom_fields.MappingField, {'child': fields.IntegerField})
        self.check_field(collections.OrderedDict[str, int], custom_fields.MappingField,
                         {'child': fields.IntegerField, 'container': collections.OrderedDict})
        self.check_field(dict[str, int], custom_fields.MappingField, {'child': fields.IntegerField, 'container': dict})
        self.check_field(dict[str, typing.Any], custom_fields.MappingField, {'container': dict})

        # check that kwargs generated for the child field are actually applied
        _, list_kwargs = self.build_typed_field(list[typing.Optional[str]])
        self.assertIsInstance(list_kwargs['child'], fields.CharField)
        self.assertTrue(list_kwargs['child'].allow_null)

        _, dict_kwargs = self.build_typed_field(dict[str, Literal['a', 'b', '']])
        self.assertIsInstance(dict_kwargs['child'], fields.ChoiceField)
        self.assertDictEqual(dict_kwargs['child'].choices, {'a': 'a', 'b': 'b'})
        self.assertTrue(dict_kwargs['child'].allow_blank)

    @unittest.skipIf(sys.version_info < (3, 10, 0), 'Python 3.10 required')
    def test_composite_pep604(self):
        self.check_field(typing.List[str] | None, custom_fields.IterableField,
                         {'child': fields.CharField, 'allow_null': True, 'container': list})
        self.check_field(typing.Dict[str, int] | None, custom_fields.MappingField,
                         {'child': fields.IntegerField, 'allow_null': True, 'container': dict})

    def test_nested(self):
        refclass = dataclasses.make_dataclass('ReferencedDataclass', [])
        self.check_field(refclass, DataclassSerializer,
                         {'dataclass': refclass, 'many': False})

        # customizing the dataclass serializer by changing the serializer_dataclass_field property
        subclassed_serializer = type('SubclassedDataclassSerializer1', (DataclassSerializer, ), {})
        setattr(DataclassSerializer, 'serializer_dataclass_field', subclassed_serializer)
        self.check_field(refclass, subclassed_serializer, {'dataclass': refclass, 'many': False})

        # customizing the dataclass serializer by putting the type into the field mapping
        subclassed_serializer = type('SubclassedDataclassSerializer2', (DataclassSerializer, ), {})
        DataclassSerializer.serializer_field_mapping[refclass] = subclassed_serializer
        self.check_field(refclass, subclassed_serializer, {'dataclass': refclass, 'many': False})

        # customizing the dataclass serializer by putting regular Field in the field mapping
        DataclassSerializer.serializer_field_mapping[refclass] = fields.CharField
        self.check_field(refclass, fields.CharField, {})

    def test_relational(self):
        django.setup()

        class Person(models.Model):
            name = models.CharField(max_length=30)

            class Meta:
                app_label = 'tests'

        self.check_field(Person, relations.PrimaryKeyRelatedField,
                         {'queryset': Person._default_manager})

        # test changing serializer_related_field, and a hyperlinked field which triggers a different code path
        DataclassSerializer.serializer_related_field = relations.HyperlinkedRelatedField
        self.check_field(Person, relations.HyperlinkedRelatedField,
                         {'queryset': Person._default_manager, 'view_name': 'person-detail'})

    def test_union(self):
        cls, kwargs = self.build_typed_field(typing.Union[str, int])
        self.assertEqual(cls, custom_fields.UnionField)
        self.assertEqual(type(kwargs['child_fields'][str]), fields.CharField)
        self.assertEqual(type(kwargs['child_fields'][int]), fields.IntegerField)

        # check that kwargs generated for the child field are applied
        _, kwargs = self.build_typed_field(typing.Union[int, Literal['a', 'b']])
        self.assertEqual(kwargs['child_fields'][Literal['a', 'b']].choices, {'a': 'a', 'b': 'b'})

        # check that child_kwargs are applied
        _, kwargs = self.build_typed_field(typing.Union[str, int], extra_kwargs={'child_kwargs': {'label': 'Test'}})
        self.assertEqual(kwargs['child_fields'][str].label, 'Test')

    def test_literal(self):
        self.check_field(Literal['a', 'b'], fields.ChoiceField,
                         {'choices': ['a', 'b'], 'allow_blank': False})
        self.check_field(Literal['a', 'b', ''], fields.ChoiceField,
                         {'choices': ['a', 'b'], 'allow_blank': True})
        self.check_field(Literal['a', 'b', None], fields.ChoiceField,
                         {'choices': ['a', 'b'], 'allow_blank': False, 'allow_null': True})
        self.check_field(Literal['a', 'b', '', None], fields.ChoiceField,
                         {'choices': ['a', 'b'], 'allow_blank': True, 'allow_null': True})

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

    def test_standard_variable(self):
        var_str = typing.TypeVar('var_str', bound=str)
        var_any = typing.TypeVar('var_any')

        self.check_field(var_str, fields.CharField)

        with self.assertRaises(NotImplementedError):
            self.build_typed_field(var_any)

    def test_standard_decimal(self):
        self.check_field(decimal.Decimal, custom_fields.DefaultDecimalField)

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
               "of type 'typing.Any' (during search for field of type 'typing.Any').")
        with self.assertRaisesRegex(NotImplementedError, re.escape(msg)):
            self.build_typed_field(typing.Any)
