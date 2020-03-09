import dataclasses
import datetime
import decimal
import typing
import unittest
import uuid

from rest_framework import fields

from rest_framework_dataclasses import field_utils
from rest_framework_dataclasses.serializers import DataclassSerializer
from rest_framework_dataclasses.types import Literal


class FieldsTest(unittest.TestCase):
    def build_typed_field(self, type_hint, extra_kwargs=None):
        testclass = dataclasses.make_dataclass('TestDataclass', [('test_field', type_hint)])
        serializer = DataclassSerializer(dataclass=testclass)
        type_info = field_utils.get_type_info(serializer.dataclass_definition.field_types['test_field'])

        extra_kwargs = extra_kwargs or {}
        return serializer.build_typed_field('test_field', type_info, extra_kwargs)

    def check_field(self, type_hint, field, kwargs=None):
        field_class, field_kwargs = self.build_typed_field(type_hint)
        self.assertIs(field, field_class, f'for field of type {type_hint}')

        if kwargs:
            self.assertDictEqual(field_kwargs, kwargs, f'arguments for field of type {type_hint}')

    def test_composite(self):
        self.check_field(typing.Iterable[str], fields.ListField)
        self.check_field(typing.Sequence[str], fields.ListField)
        self.check_field(typing.List[str], fields.ListField)

        self.check_field(typing.Mapping[str, int], fields.DictField)
        self.check_field(typing.Dict[str, int], fields.DictField)

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

    def test_nested(self):
        refclass = dataclasses.make_dataclass('ReferencedDataclass', [])
        self.check_field(refclass, DataclassSerializer,
                         {'dataclass': refclass, 'many': False})
        self.check_field(typing.Optional[refclass], DataclassSerializer,
                         {'dataclass': refclass, 'many': False, 'required': False, 'allow_null': True})

    def test_relational(self):
        # TODO
        pass

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
               "of type '<class 'complex'>'.")
        with self.assertRaisesRegex(NotImplementedError, msg):
            self.build_typed_field(complex)

        # Check _SpecialForm types that don't have an __mro__attribute (#6)
        msg = ("Automatic serializer field deduction not supported for field 'test_field' on 'TestDataclass' "
               "of type 'typing.Any'.")
        with self.assertRaisesRegex(NotImplementedError, msg):
            self.build_typed_field(typing.Any)
