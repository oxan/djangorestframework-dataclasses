import copy
import datetime
import uuid

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
        self.assertEqual(len(f), 9)

        self.assertIsInstance(f['id'], fields.UUIDField)
        self.assertFalse(f['id'].allow_null)

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


class SerializationTestCase(TestCase):
    person_instance = fixtures.alice
    person_serialized = {
        'id': str(person_instance.id),
        'name': person_instance.name,
        'email': person_instance.email,
        'alive': person_instance.alive,
        'phone': person_instance.phone,
        'weight': person_instance.weight,
        'birth_date': person_instance.birth_date.isoformat(),
        'movie_ratings': person_instance.movie_ratings
    }

    class PersonSerializer(DataclassSerializer):
        class Meta:
            dataclass = fixtures.Person

    def test_serialize(self):
        serializer = self.PersonSerializer(instance=self.person_instance)
        self.assertDictEqual(serializer.data, self.person_serialized)

    def test_deserialize(self):
        serializer = self.PersonSerializer(data=self.person_serialized)
        serializer.is_valid(raise_exception=True)
        result = serializer.validated_data

        self.assertIsInstance(result['id'], uuid.UUID)
        self.assertIsInstance(result['alive'], bool)
        self.assertIsInstance(result['weight'], float)
        self.assertIsInstance(result['birth_date'], datetime.date)
        self.assertIsInstance(result['movie_ratings'], dict)

    def test_create(self):
        serializer = self.PersonSerializer(data=self.person_serialized)
        serializer.is_valid(raise_exception=True)
        person = serializer.save()

        self.assertIsInstance(person, fixtures.Person)
        self.assertEqual(person, self.person_instance)

    def test_update(self):
        instance = copy.deepcopy(fixtures.charlie)
        serializer = self.PersonSerializer(instance=instance, data=self.person_serialized)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        self.assertIsInstance(result, fixtures.Person)
        self.assertIs(result, instance)
        self.assertEqual(result, self.person_instance)


class NestedSerializationTestCase(TestCase):
    house_dataclass = fixtures.alices_house
    house_serialized = {
        'address': house_dataclass.address,
        'owner': {
            'id': str(house_dataclass.owner.id),
            'name': house_dataclass.owner.name,
            'email': house_dataclass.owner.email,
            'alive': house_dataclass.owner.alive,
            'phone': house_dataclass.owner.phone,
            'weight': house_dataclass.owner.weight,
            'birth_date': house_dataclass.owner.birth_date.isoformat(),
            'movie_ratings': house_dataclass.owner.movie_ratings
        },
        'residents': [
            {
                'id': str(house_dataclass.residents[0].id),
                'name': house_dataclass.residents[0].name,
                'email': house_dataclass.residents[0].email,
                'alive': house_dataclass.residents[0].alive,
                'phone': house_dataclass.residents[0].phone,
                'weight': None,
                'birth_date': None,
                'movie_ratings': None
            }
        ],
        'room_area': house_dataclass.room_area
    }

    def test_create(self):
        serializer = DataclassSerializer(dataclass=fixtures.House, data=self.house_serialized)
        serializer.is_valid(raise_exception=True)
        house = serializer.save()

        self.assertIsInstance(house, fixtures.House)
        self.assertIsInstance(house.owner, fixtures.Person)
        self.assertIsInstance(house.residents, list)
        self.assertIsInstance(house.residents[0], fixtures.Person)
        self.assertIsInstance(house.room_area, dict)
        self.assertEqual(house, self.house_dataclass)


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
