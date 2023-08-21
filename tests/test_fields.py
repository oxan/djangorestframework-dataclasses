import collections
import enum

from unittest import TestCase

from django.core.exceptions import ImproperlyConfigured
from rest_framework import fields
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import Serializer

from rest_framework_dataclasses.fields import DefaultDecimalField, EnumField, IterableField, MappingField, UnionField


class FieldTest(TestCase):
    def test_decimal_field(self):
        # check no parameters are required (this shouldn't throw)
        field = DefaultDecimalField()

        # check no parameters are overwritten
        field = DefaultDecimalField(max_digits=4, decimal_places=6)
        self.assertEqual(field.max_digits, 4)
        self.assertEqual(field.decimal_places, 6)

    def test_enum_field(self):
        class Color(enum.Enum):
            RED = 'FF0000'
            GREEN = '00FF00'
            BLUE = '0000FF'

        field = EnumField(Color)
        self.assertDictEqual(field.choices, {'FF0000': 'RED', '00FF00': 'GREEN', '0000FF': 'BLUE'})
        self.assertEqual(field.to_representation(Color.GREEN), '00FF00')
        self.assertEqual(field.to_internal_value('00FF00'), Color.GREEN)
        with self.assertRaises(ValidationError):
            field.to_internal_value('RED')

        field = EnumField(Color, by_name=True)
        self.assertDictEqual(field.choices, {'RED': 'RED', 'GREEN': 'GREEN', 'BLUE': 'BLUE'})
        self.assertEqual(field.to_internal_value('GREEN'), Color.GREEN)
        self.assertEqual(field.to_representation(Color.GREEN), 'GREEN')
        with self.assertRaises(ValidationError):
            field.to_internal_value('FF0000')

        self.assertEqual(field.to_representation('RED'), 'RED')
        with self.assertRaises(ValidationError):
            field.to_representation('FFFFFF')

        # check explicit specification of options
        field = EnumField(Color, choices=[('FF0000', 'RED'), ('00FF00', 'GREEN')])
        self.assertEqual(len(field.choices), 2)

    def test_iterable_field(self):
        default_field = IterableField()
        self.assertEqual(default_field.to_internal_value(['foo', 'bar']), ['foo', 'bar'])

        set_field = IterableField(container=set)
        self.assertEqual(set_field.to_internal_value(['foo', 'bar', 'baz']), {'foo', 'bar', 'baz'})

    def test_mapping_field(self):
        default_field = MappingField()
        self.assertEqual(default_field.to_internal_value({'foo': 'bar'}), {'foo': 'bar'})

        ordered_field = MappingField(container=collections.OrderedDict)
        ordered_values = {'foo': 'bar', 'abc': 'def'}
        self.assertEqual(ordered_field.to_internal_value(ordered_values), collections.OrderedDict(ordered_values))

    def test_union_field(self):
        class A:
            def __init__(self, a):
                self.a = a

        class B:
            def __init__(self, b):
                self.b = b

        class ASerializer(Serializer):
            a = fields.CharField()

        class BSerializer(Serializer):
            b = fields.IntegerField()

        # Note that A/B are regular classes and serializers, so internal value is a dict and not a dataclass.
        ab_field = UnionField({A: ASerializer, B: BSerializer}, nest_value=False)
        self.assertEqual(ab_field.to_internal_value({'type': 'A', 'a': 'a'}), {'a': 'a'})
        self.assertEqual(ab_field.to_internal_value({'type': 'B', 'b': 42}), {'b': 42})
        self.assertEqual(ab_field.to_representation(A('a')), {'type': 'A', 'a': 'a'})
        self.assertEqual(ab_field.to_representation(B(42)), {'type': 'B', 'b': 42})

        strint_field = UnionField({str: fields.CharField, int: fields.IntegerField}, nest_value=True)
        self.assertEqual(strint_field.to_internal_value({'type': 'str', 'value': 'hello'}), 'hello')
        self.assertEqual(strint_field.to_internal_value({'type': 'int', 'value': 42}), 42)
        self.assertEqual(strint_field.to_representation('hello'), {'type': 'str', 'value': 'hello'})
        self.assertEqual(strint_field.to_representation(42), {'type': 'int', 'value': 42})

        with self.assertRaises(ValidationError):
            strint_field.to_internal_value({'value': 3})
        with self.assertRaises(ValidationError):
            strint_field.to_internal_value({'type': 'int'})
        with self.assertRaises(ValidationError):
            strint_field.to_internal_value({'type': 'int', 'value': 3.5})
        with self.assertRaises(ValidationError):
            strint_field.to_internal_value({'type': 'float', 'value': 3})

        invalid_field = UnionField({str: fields.CharField, int: fields.IntegerField}, nest_value=False)
        with self.assertRaises(ImproperlyConfigured):
            invalid_field.to_representation(42)

        renamed_field = UnionField({int: fields.IntegerField, float: fields.FloatField},
                                   nest_value=True,
                                   discriminator_field_name='renamed_type',
                                   value_field_name='renamed_value')
        self.assertEqual(renamed_field.to_internal_value({'renamed_type': 'float', 'renamed_value': 1.2}), 1.2)
        self.assertEqual(renamed_field.to_representation(3.4), {'renamed_type': 'float', 'renamed_value': 3.4})
