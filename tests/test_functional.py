import copy
import datetime
import uuid

from unittest import TestCase

from rest_framework import fields, serializers
from rest_framework_dataclasses.serializers import DataclassSerializer

from . import fixtures


class SerializationTestCase(TestCase):
    person_instance = fixtures.alice
    person_serialized = {
        'id': str(person_instance.id),
        'name': person_instance.name,
        'email': person_instance.email,
        'alive': person_instance.alive,
        'gender': person_instance.gender,
        'phone': person_instance.phone,
        'weight': person_instance.weight,
        'birth_date': person_instance.birth_date.isoformat(),
        'movie_ratings': person_instance.movie_ratings,
        'age': person_instance.age()
    }

    class PersonSerializer(DataclassSerializer):
        class Meta:
            dataclass = fixtures.Person
            fields = (serializers.ALL_FIELDS, 'age')

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
    street_dataclass = fixtures.abbey_road
    street_serialized = {
        'name': street_dataclass.name,
        'length': '7.25',
        'houses': {
            '123': {
                'address': street_dataclass.houses['123'].address,
                'owner': {
                    'id': str(street_dataclass.houses['123'].owner.id),
                    'name': street_dataclass.houses['123'].owner.name,
                    'email': street_dataclass.houses['123'].owner.email,
                    'alive': street_dataclass.houses['123'].owner.alive,
                    'gender': street_dataclass.houses['123'].owner.gender,
                    'phone': street_dataclass.houses['123'].owner.phone,
                    'weight': street_dataclass.houses['123'].owner.weight,
                    'birth_date': street_dataclass.houses['123'].owner.birth_date.isoformat(),
                    'movie_ratings': street_dataclass.houses['123'].owner.movie_ratings
                },
                'residents': [
                    {
                        'id': str(street_dataclass.houses['123'].residents[0].id),
                        'name': street_dataclass.houses['123'].residents[0].name,
                        'email': street_dataclass.houses['123'].residents[0].email,
                        'alive': street_dataclass.houses['123'].residents[0].alive,
                        'gender': street_dataclass.houses['123'].residents[0].gender,
                        'phone': street_dataclass.houses['123'].residents[0].phone,
                        'weight': None,
                        'birth_date': None,
                        'movie_ratings': None
                    }
                ],
                'room_area': street_dataclass.houses['123'].room_area
            }
        }
    }

    class StreetSerializer(DataclassSerializer):
        length = fields.DecimalField(max_digits=3, decimal_places=2)

        class Meta:
            dataclass = fixtures.Street


    def test_create(self):
        serializer = self.StreetSerializer(data=self.street_serialized)
        serializer.is_valid(raise_exception=True)
        street = serializer.save()

        self.assertIsInstance(street, fixtures.Street)
        self.assertIsInstance(street.houses, dict)
        self.assertIsInstance(street.houses['123'], fixtures.House)
        self.assertIsInstance(street.houses['123'].owner, fixtures.Person)
        self.assertIsInstance(street.houses['123'].residents, list)
        self.assertIsInstance(street.houses['123'].residents[0], fixtures.Person)
        self.assertIsInstance(street.houses['123'].room_area, dict)
        self.assertEqual(street, self.street_dataclass)