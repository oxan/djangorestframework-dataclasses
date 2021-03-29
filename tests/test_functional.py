import copy
import dataclasses
import datetime
import decimal
import enum
import typing
import uuid

from unittest import TestCase

from rest_framework import fields

from rest_framework_dataclasses.serializers import DataclassSerializer
from rest_framework_dataclasses.types import Literal


class Gender(enum.Enum):
    MALE = 'male'
    FEMALE = 'female'
    OTHER = 'other'


@dataclasses.dataclass
class Pet:
    animal: Literal['cat', 'dog']
    name: str
    weight: typing.Optional[decimal.Decimal] = \
        dataclasses.field(default=None, metadata={'serializer_kwargs': {'max_digits': 4, 'decimal_places': 1}})


class PetSerializer(DataclassSerializer):
    class Meta:
        dataclass = Pet


@dataclasses.dataclass
class Person:
    id: uuid.UUID
    name: str
    email: str
    phone: typing.List[str]
    gender: typing.Optional[Gender] = None
    length: typing.Optional[decimal.Decimal] = None
    pets: typing.Optional[typing.List[Pet]] = None
    birth_date: typing.Optional[datetime.date] = None
    favorite_pet: typing.Optional[Pet] = \
        dataclasses.field(default=None, metadata={'serializer_field': PetSerializer(allow_null=True)})
    movie_ratings: typing.Optional[typing.Dict[str, int]] = None

    def age(self) -> int:
        # don't use current date to keep test deterministic, and we don't care that this calculation is actually wrong.
        return datetime.date(2020, 1, 1).year - self.birth_date.year if self.birth_date else None


class PersonSerializer(DataclassSerializer):
    full_name = fields.CharField(source='name')
    email = fields.EmailField()
    slug = fields.SlugField(source='name', read_only=True)

    class Meta:
        dataclass = Person
        fields = ('id', 'full_name', 'email', 'phone', 'gender', 'length', 'pets', 'birth_date', 'favorite_pet',
                  'movie_ratings', 'slug', 'age')
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

    def test_validated_data(self):
        serializer = self.serializer(data=self.representation)
        serializer.is_valid(raise_exception=True)

        self.assertEqual(serializer.validated_data, self.instance)

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
        length=decimal.Decimal('1.68'),
        phone=['+31-6-1234-5678', '+31-20-123-4567'],
        gender=Gender.FEMALE,
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
        'length': '1.68',
        'phone': ['+31-6-1234-5678', '+31-20-123-4567'],
        'gender': 'female',
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
        'favorite_pet': None,
    }
    representation_readonly = {
        'slug': 'Alice',
        'length': None,
        'gender': None,
        'pets': None,
        'birth_date': None,
        'age': None,
        'movie_ratings': None
    }


class PartialPersonTest(TestCase):
    def test_update(self):
        input_instance = Person(
            id=uuid.UUID('28ee3ae5-480b-46bd-9ae4-c61cf8341b95'),
            name='Alice',
            email='alice@example.com',
            phone=['+31-6-1234-5678', '+31-20-123-4567'],
            favorite_pet=Pet('cat', 'Luna'),
            pets=[Pet('dog', 'Bella'), Pet('cat', 'Luna')],
        )

        partial_representation = {
            'full_name': 'Bob',
            'email': 'bob@example.com',
            'favorite_pet': {'name': 'Molly'},
            'pets': [{'animal': 'cat', 'name': 'Molly'}],
        }

        expected_output = dataclasses.replace(input_instance,
                                              name='Bob',
                                              email='bob@example.com',
                                              favorite_pet=Pet(animal='cat', name='Molly'),
                                              pets=[Pet('cat', 'Molly')])

        serializer = PersonSerializer(instance=input_instance, data=partial_representation, partial=True)
        serializer.is_valid(raise_exception=True)
        output_instance = serializer.save()

        self.assertIs(output_instance, input_instance)
        self.assertEqual(output_instance, expected_output)
