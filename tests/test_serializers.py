from dataclasses import dataclass
from unittest import TestCase

from django.core.exceptions import ImproperlyConfigured
from rest_framework import fields, serializers
from rest_framework_dataclasses.serializers import DataclassSerializer

from . import fixtures


class SerializerTestCase(TestCase):
    def test_person(self):
        class PersonSerializer(DataclassSerializer):
            email = fields.EmailField()

            class Meta:
                dataclass = fixtures.Person
                fields = (serializers.ALL_FIELDS, 'age')
                read_only_fields = ('birth_date', )

        serializer = PersonSerializer()
        f = serializer.get_fields()
        self.assertEqual(len(f), 8)

        self.assertIsInstance(f['name'], fields.CharField)
        self.assertFalse(f['name'].allow_null)

        self.assertIsInstance(f['email'], fields.EmailField)

        self.assertIsInstance(f['alive'], fields.BooleanField)
        self.assertFalse(f['alive'].allow_null)

        self.assertIsInstance(f['weight'], fields.FloatField)
        self.assertTrue(f['weight'].allow_null)

        self.assertIsInstance(f['birth_date'], fields.DateField)
        self.assertTrue(f['birth_date'].read_only)

        self.assertIsInstance(f['phone'], fields.ListField)
        self.assertFalse(f['phone'].allow_null)
        self.assertIsInstance(f['phone'].child, fields.CharField)
        self.assertFalse(f['phone'].child.allow_null)

        self.assertIsInstance(f['movie_ratings'], fields.DictField)
        self.assertTrue(f['movie_ratings'].allow_null)
        self.assertIsInstance(f['movie_ratings'].child, fields.IntegerField)
        self.assertFalse(f['movie_ratings'].child.allow_null)

        self.assertIsInstance(f['age'], fields.ReadOnlyField)

    def test_exclude(self):
        class PetSerializer(DataclassSerializer):
            class Meta:
                dataclass = fixtures.Pet
                exclude = ('animal', )

        serializer = PetSerializer()
        f = serializer.get_fields()
        self.assertNotIn('animal', f)

    def test_extra_kwargs(self):
        class StreetSerializer(DataclassSerializer):
            class Meta:
                dataclass = fixtures.Street
                extra_kwargs = {
                    'length': {'max_digits': 3, 'decimal_places': 2},
                    'houses': {'label': 'Houses on street', 'child_kwargs': {
                        'extra_kwargs': {
                            'address': {'max_length': 20},
                            'owner': {'label': 'House owner'},
                            'residents': {'child_kwargs': {
                                'extra_kwargs': {
                                    'movie_ratings': {'child_kwargs': {'min_value': 0, 'max_value': 10}}
                                }
                            }
                        }}
                    }}
                }

        serializer = StreetSerializer()
        f = serializer.get_fields()

        self.assertIsInstance(f['length'], fields.DecimalField)
        self.assertEqual(f['length'].decimal_places, 2)
        self.assertEqual(f['length'].max_digits, 3)

        self.assertEqual(f['houses'].label, 'Houses on street')

        house_fields = f['houses'].child.get_fields()
        self.assertEqual(house_fields['address'].max_length, 20)
        self.assertEqual(house_fields['owner'].label, 'House owner')

        resident_fields = house_fields['residents'].child.get_fields()
        self.assertEqual(resident_fields['movie_ratings'].child.min_value, 0)
        self.assertEqual(resident_fields['movie_ratings'].child.max_value, 10)


class ErrorsTestCase(TestCase):
    def test_invalid_dataclass_specification(self):
        class ExplicitPersonSerializer(DataclassSerializer):
            class Meta:
                dataclass = fixtures.Person

        class AnonymousPersonSerializer(DataclassSerializer):
            class Meta:
                pass

        with self.assertRaises(AssertionError):
            ExplicitPersonSerializer(dataclass=fixtures.Person).get_fields()

        with self.assertRaises(AssertionError):
            AnonymousPersonSerializer().get_fields()

    def test_non_dataclass(self):
        class Empty:
            pass

        with self.assertRaises(ValueError):
            DataclassSerializer(dataclass=Empty).get_fields()

    def test_field_specification(self):
        class InvalidSerializer(DataclassSerializer):
            email = serializers.EmailField()

            class Meta:
                dataclass = fixtures.Person

        # invalid `fields` specification
        InvalidSerializer.Meta.fields = 'invalid'
        with self.assertRaises(TypeError):
            InvalidSerializer().get_fields()

        # declared field not in `fields`
        InvalidSerializer.Meta.fields = ('name', 'age')
        with self.assertRaises(AssertionError):
            InvalidSerializer().get_fields()

        # both `fields` and `exclude` specified
        InvalidSerializer.Meta.exclude = ('name', 'email')
        with self.assertRaises(AssertionError):
            InvalidSerializer().get_fields()

        del InvalidSerializer.Meta.fields

        # invalid `exclude` specification
        InvalidSerializer.Meta.exclude = 'invalid'
        with self.assertRaises(TypeError):
            InvalidSerializer().get_fields()

        # declared field in `exclude`
        InvalidSerializer.Meta.exclude = ('name', 'email')
        with self.assertRaises(AssertionError):
            InvalidSerializer().get_fields()

        # non-existing field in `exclude`
        InvalidSerializer.Meta.exclude = ('name', 'nonexisting')
        with self.assertRaises(AssertionError):
            InvalidSerializer().get_fields()

        InvalidSerializer.Meta.exclude = ('name', )

        # invalid `read_only_fields` specification
        InvalidSerializer.Meta.read_only_fields = 'invalid'
        with self.assertRaises(TypeError):
            InvalidSerializer().get_fields()

        del InvalidSerializer.Meta.read_only_fields

        # wrong spelling of `read_only_fields`
        InvalidSerializer.Meta.readonly_fields = ('name', )
        with self.assertRaises(AssertionError):
            InvalidSerializer().get_fields()

    def test_unknown_field_type(self):
        class NotSerializable:
            pass

        @dataclass
        class Example:
            f: NotSerializable

        with self.assertRaises(NotImplementedError):
            DataclassSerializer(dataclass=Example).get_fields()

    def test_unknown_field(self):
        class UnknownSerializer(DataclassSerializer):
            class Meta:
                dataclass = fixtures.Person
                fields = ('spouse', )

        with self.assertRaises(ImproperlyConfigured):
            UnknownSerializer().get_fields()
