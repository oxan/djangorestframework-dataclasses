import copy
import dataclasses
import datetime
import decimal
import typing
import uuid

from unittest import TestCase

from rest_framework import fields, serializers

from rest_framework_dataclasses.serializers import DataclassSerializer
from rest_framework_dataclasses.types import Literal


@dataclasses.dataclass
class Pet:
    animal: Literal['cat', 'dog']
    name: str
    weight: typing.Optional[decimal.Decimal] = None


@dataclasses.dataclass
class Person:
    id: uuid.UUID
    name: str
    email: str
    phone: typing.List[str]
    pets: typing.Optional[typing.List[Pet]] = None
    birth_date: typing.Optional[datetime.date] = None
    favorite_pet: typing.Optional[Pet] = None
    movie_ratings: typing.Optional[typing.Dict[str, int]] = None

    def age(self) -> int:
        # don't use current date to keep test deterministic, and we don't care that this calculation is actually wrong.
        return datetime.date(2020, 1, 1).year - self.birth_date.year if self.birth_date else None


class PetSerializer(DataclassSerializer):
    weight = fields.DecimalField(required=False, allow_null=True, max_digits=4, decimal_places=1)

    class Meta:
        dataclass = Pet


class PersonSerializer(DataclassSerializer):
    full_name = fields.CharField(source='name')
    email = fields.EmailField()
    favorite_pet = PetSerializer(allow_null=True)
    slug = fields.SlugField(source='name', read_only=True)

    class Meta:
        dataclass = Person
        fields = ('id', 'full_name', 'email', 'phone', 'pets', 'birth_date', 'favorite_pet', 'movie_ratings', 'slug', 'age')
        extra_kwargs = {
            'id': {'format': 'hex'},
            'phone': {'child_kwargs': {'max_length': 15}},
            'pets': {'child_kwargs': {'extra_kwargs': {'weight': {'max_digits': 4, 'decimal_places': 1}}}},
        }


# noinspection PyUnresolvedReferences
class FunctionalTestMixin:
    def test_serialize(self):
        serializer = self.serializer(instance=self.instance)
        self.assertDictEqual(serializer.data, {**self.representation, **self.representation_readonly})

    def test_create(self: TestCase):
        serializer = self.serializer(data=self.representation)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        self.assertEqual(instance, self.instance)

    def test_update(self: TestCase):
        empty_instance = copy.deepcopy(self.instance)
        for field in dataclasses.fields(empty_instance):
            setattr(empty_instance, field.name, None)

        serializer = self.serializer(instance=empty_instance, data=self.representation)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        self.assertIs(instance, empty_instance)
        self.assertEqual(instance, self.instance)


class PetTest(TestCase, FunctionalTestMixin):
    serializer = PetSerializer
    instance = Pet(animal='cat', name='Milo')
    representation = {'animal': 'cat', 'name': 'Milo', 'weight': None}
    representation_readonly = {}


class PersonTest(TestCase, FunctionalTestMixin):
    maxDiff = None
    serializer = PersonSerializer
    instance = Person(
        id=uuid.UUID('28ee3ae5-480b-46bd-9ae4-c61cf8341b95'),
        name='Alice',
        email='alice@example.com',
        phone=['+31-6-1234-5678', '+31-20-123-4567'],
        pets=[Pet(animal='cat', name='Milo', weight=decimal.Decimal('10.8')),
              Pet(animal='dog', name='Max', weight=decimal.Decimal('123.4'))],
        birth_date=datetime.date(1980, 4, 1),
        favorite_pet=Pet(animal='cat', name='Luna', weight=None),
        movie_ratings={'Star Wars': 8, 'Titanic': 4}
    )
    representation = {
        'id': '28ee3ae5480b46bd9ae4c61cf8341b95',
        'full_name': 'Alice',
        'email': 'alice@example.com',
        'phone': ['+31-6-1234-5678', '+31-20-123-4567'],
        'pets': [
            {'animal': 'cat', 'name': 'Milo', 'weight': '10.8'},
            {'animal': 'dog', 'name': 'Max', 'weight': '123.4'}
        ],
        'birth_date': '1980-04-01',
        'age': 40,
        'favorite_pet': {'animal': 'cat', 'name': 'Luna', 'weight': None},
        'movie_ratings': {'Star Wars': 8, 'Titanic': 4},
    }
    representation_readonly = {
        'slug': 'Alice'
    }


class EmptyPersonTest(TestCase, FunctionalTestMixin):
    serializer = PersonSerializer
    instance = Person(
        id=uuid.UUID('28ee3ae5-480b-46bd-9ae4-c61cf8341b95'),
        name='Alice',
        email='alice@example.com',
        phone=[],
    )
    representation = {
        'id': '28ee3ae5480b46bd9ae4c61cf8341b95',
        'full_name': 'Alice',
        'email': 'alice@example.com',
        'phone': [],
        'pets': None,
        'birth_date': None,
        'age': None,
        'favorite_pet': None,
        'movie_ratings': None
    }
    representation_readonly = {
        'slug': 'Alice'
    }
