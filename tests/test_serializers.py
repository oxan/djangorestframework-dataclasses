import copy
import dataclasses
import datetime
import typing

from unittest import TestCase

from django.core.exceptions import ImproperlyConfigured
from rest_framework import fields, serializers
from rest_framework_dataclasses.serializers import DataclassSerializer


@dataclasses.dataclass
class Person:
    name: str
    length: int
    birth_date: typing.Optional[datetime.date] = None

    def age(self) -> int:
        return 1


class SerializerTest(TestCase):
    def create_serializer(self, dataclass=None, arguments=None, declared=None, meta=None) -> DataclassSerializer:
        arguments = arguments or {}
        classdict = declared or {}

        if meta is not None:
            if dataclass:
                meta['dataclass'] = dataclass
            classdict['Meta'] = type('Meta', (), meta)
        elif dataclass:
            arguments['dataclass'] = dataclass

        serializer_type = type('TestSerializer', (DataclassSerializer, ), classdict)
        return serializer_type(**arguments)

    def test_definition(self):
        definition = self.create_serializer(Person).dataclass_definition
        self.assertIs(definition.dataclass_type, Person)
        self.assertIn('name', definition.fields)
        self.assertEqual(definition.field_types['name'], str)
        self.assertIn('length', definition.fields)
        self.assertEqual(definition.field_types['length'], int)
        self.assertIn('birth_date', definition.fields)
        self.assertEqual(definition.field_types['birth_date'], typing.Optional[datetime.date])

        # both `dataclass` and `Meta` specified
        with self.assertRaises(AssertionError):
            definition = self.create_serializer(arguments={'dataclass': Person},
                                                meta={}).dataclass_definition

        # no `dataclass` parameter and missing `Meta`
        with self.assertRaises(AssertionError):
            definition = self.create_serializer().dataclass_definition

        # no `dataclass` parameter and invalid `Meta`
        with self.assertRaises(AssertionError):
            definition = self.create_serializer(meta={}).dataclass_definition

        # non-dataclass
        with self.assertRaises(ValueError):
            definition = self.create_serializer(str).dataclass_definition

    def test_save(self):
        def mock_person_serializer(data, instance=None):
            serializer = self.create_serializer(Person)
            serializer._errors = []
            serializer._validated_data = data
            if not hasattr(serializer._validated_data, '_unsupplied_fields'):
                serializer._validated_data._unsupplied_fields = []
            if instance:
                serializer.instance = instance
            return serializer

        alice = Person(name='Alice', length=123)

        # regular create
        ser = mock_person_serializer(alice)
        self.assertEqual(ser.save(), alice)

        # regular update
        inst = dataclasses.replace(alice)
        ser = mock_person_serializer(alice, instance=inst)
        self.assertIs(ser.save(), inst)
        self.assertEqual(ser.save(), alice)

        # create with kwargs
        ser = mock_person_serializer(alice)
        self.assertEqual(ser.save(length=456), dataclasses.replace(alice, length=456))

        # update with kwargs
        inst = dataclasses.replace(alice, name='Bob', length=789)
        ser = mock_person_serializer(alice, instance=inst)
        self.assertIs(ser.save(length=456), inst)
        self.assertEqual(ser.save(length=456), dataclasses.replace(alice, length=456))

        # full update with set of field to default value
        inst = dataclasses.replace(alice, birth_date=datetime.datetime(2020, 2, 2))
        ser = mock_person_serializer(alice, instance=inst)
        self.assertIs(ser.save(), inst)
        self.assertEqual(ser.save().birth_date, None)

        # partial update with missing optional field
        data = dataclasses.replace(alice)
        data._unsupplied_fields = ["birth_date"]
        inst = dataclasses.replace(alice, birth_date=datetime.datetime(2020, 2, 2))
        ser = mock_person_serializer(data, instance=inst)
        self.assertIs(ser.save(), inst)
        self.assertEqual(ser.save().birth_date, datetime.datetime(2020, 2, 2))

        # not validated
        with self.assertRaises(AssertionError):
            self.create_serializer(Person).save()

    def test_nested_save(self):
        def check(dataclass, representation, instance):
            empty_instance = copy.deepcopy(instance)
            for field in dataclasses.fields(empty_instance):
                setattr(empty_instance, field.name, None)

            serializer = self.create_serializer(dataclass, arguments={'data': representation})
            self.assertTrue(serializer.is_valid(raise_exception=False))
            self.assertEqual(serializer.save(), instance)

            serializer = self.create_serializer(dataclass, arguments={'data': representation,
                                                                      'instance': empty_instance})
            self.assertTrue(serializer.is_valid(raise_exception=False))
            self.assertEqual(serializer.save(), instance)

        # simple dataclass with a single field
        simple = dataclasses.make_dataclass('child', [('value', str)])
        check(simple, {'value': 'A'}, simple('A'))

        # nested dataclass
        parent = dataclasses.make_dataclass('parent', [('field', simple)])
        check(parent, {'field': {'value': 'A'}}, parent(simple('A')))

        # a nested dataclass that's optional
        optional = dataclasses.make_dataclass('optional', [('field', typing.Optional[simple])])
        check(optional, {'field': {'value': 'A'}}, optional(simple('A')))
        check(optional, {'field': None}, optional(None))

        # we check all possible kinds of (optionally) nested dataclasses in lists and dictionaries here, as historically
        # this code has given us quite some problems (#13, #15).
        # a list of nested dataclasses
        listvalue = dataclasses.make_dataclass('listvalue',
                                               [('field', typing.Iterable[simple])])
        check(listvalue, {'field': []}, listvalue([]))
        check(listvalue, {'field': [{'value': 'A'}]}, listvalue([simple('A')]))

        # an optional list of nested dataclasses
        optionallist = dataclasses.make_dataclass('optionallist',
                                                  [('field', typing.Optional[typing.List[simple]])])
        check(optionallist, {'field': None}, optionallist(None))
        check(optionallist, {'field': []}, optionallist([]))
        check(optionallist, {'field': [{'value': 'A'}]}, optionallist([simple('A')]))

        # a list of optional nested dataclasses
        listoptional = dataclasses.make_dataclass('listoptional',
                                                  [('field', typing.List[typing.Optional[simple]])])
        check(listoptional, {'field': []}, listoptional([]))
        check(listoptional, {'field': [None]}, listoptional([None]))
        check(listoptional, {'field': [{'value': 'A'}]}, listoptional([simple('A')]))

        # a dictionary of nested dataclasses
        dictvalue = dataclasses.make_dataclass('dictvalue',
                                               [('field', typing.Mapping[str, simple])])
        check(dictvalue, {'field': {}}, dictvalue({}))
        check(dictvalue, {'field': {'K': {'value': 'A'}}}, dictvalue({'K': simple('A')}))

        # an optional dictionary of nested dataclasses
        optionaldict = dataclasses.make_dataclass('optionaldict',
                                                  [('field', typing.Optional[typing.Dict[str, simple]])])
        check(optionaldict, {'field': None}, optionaldict(None))
        check(optionaldict, {'field': {}}, optionaldict({}))
        check(optionaldict, {'field': {'K': {'value': 'A'}}}, optionaldict({'K': simple('A')}))

        # a dictionary of optional nested dataclasses
        dictoptional = dataclasses.make_dataclass('dictoptional',
                                                  [('field', typing.Dict[str, typing.Optional[simple]])])
        check(dictoptional, {'field': {}}, dictoptional({}))
        check(dictoptional, {'field': {'K': None}}, dictoptional({'K': None}))
        check(dictoptional, {'field': {'K': {'value': 'A'}}}, dictoptional({'K': simple('A')}))

    def test_get_fields(self):
        f = self.create_serializer(Person,
                                   declared={'slug': fields.SlugField(source='name')},
                                   meta={'read_only_fields': ['birth_date'],
                                         'extra_kwargs': {'name': {'max_length': 15}}}).get_fields()

        self.assertEqual(len(f), 4)

        self.assertIsInstance(f['name'], fields.CharField)
        self.assertTrue(f['name'].required)
        self.assertEqual(f['name'].max_length, 15)

        self.assertIsInstance(f['length'], fields.IntegerField)

        self.assertIsInstance(f['birth_date'], fields.DateField)
        self.assertTrue(f['birth_date'].read_only)

        self.assertIsInstance(f['slug'], fields.SlugField)
        self.assertEqual(f['slug'].source, 'name')

        with self.assertRaises(AssertionError):
            self.create_serializer(Person,
                                   declared={'slug': fields.SlugField(source='name')},
                                   meta={'read_only_fields': ['slug']}).get_fields()

    def test_get_field_names(self):
        def check(serializer, expected):
            self.assertListEqual(serializer.get_field_names(), expected)

        check(self.create_serializer(Person),
              ['name', 'length', 'birth_date'])
        check(self.create_serializer(Person, meta={'fields': ['name', 'length']}),
              ['name', 'length'])
        check(self.create_serializer(Person, meta={'fields': serializers.ALL_FIELDS}),
              ['name', 'length', 'birth_date'])
        check(self.create_serializer(Person, meta={'fields': (serializers.ALL_FIELDS, 'age')}),
              ['age', 'name', 'length', 'birth_date'])
        check(self.create_serializer(Person, meta={'fields': ('age', )}),
              ['age'])
        check(self.create_serializer(Person, meta={'exclude': ['name']}),
              ['length', 'birth_date'])
        check(self.create_serializer(Person, declared={'age': fields.ReadOnlyField()}),
              ['age', 'name', 'length', 'birth_date'])

        # invalid `fields` specification
        with self.assertRaises(TypeError):
            self.create_serializer(Person, meta={'fields': 'invalid'}).get_field_names()

        # invalid `exclude` specification
        with self.assertRaises(TypeError):
            self.create_serializer(Person, meta={'exclude': 'invalid'}).get_field_names()

        # declared field not in `fields`
        with self.assertRaises(AssertionError):
            self.create_serializer(Person,
                                   declared={'name': fields.SlugField()},
                                   meta={'fields': ['length']}).get_field_names()

        # declared field in `exclude`
        with self.assertRaises(AssertionError):
            self.create_serializer(Person,
                                   declared={'name': fields.SlugField()},
                                   meta={'exclude': ['name']}).get_field_names()

        # non-existing field in `fields`
        with self.assertRaises(AssertionError):
            self.create_serializer(Person, meta={'fields': ['nonexisting']}).get_field_names()

        # non-existing field in `exclude`
        with self.assertRaises(AssertionError):
            self.create_serializer(Person, meta={'exclude': ['nonexisting']}).get_field_names()

        # both `fields` and `exclude` specified
        with self.assertRaises(AssertionError):
            self.create_serializer(Person, meta={'fields': ['name'], 'exclude': ['length']}).get_field_names()

    def test_create_field(self):
        serializer = self.create_serializer(Person)

        # From a field
        name_field = serializer.create_field('name', {'max_length': 20, 'trim_whitespace': False})
        self.assertIsInstance(name_field, fields.CharField)
        self.assertEqual(name_field.max_length, 20)
        self.assertEqual(name_field.trim_whitespace, False)

        # Function field
        age_field = serializer.create_field('age', {})
        self.assertIsInstance(age_field, fields.ReadOnlyField)

        # Aliased field
        aliased_field = serializer.create_field('aliased', {'source': 'name'})
        self.assertIsInstance(aliased_field, fields.CharField)
        self.assertEqual(aliased_field.source, 'name')

        # Aliased to non-existing field
        with self.assertRaises(ImproperlyConfigured):
            unknown_field = serializer.create_field('aliased', {'source': 'nonexisting'})

    def test_include_extra_kwargs(self):
        serializer = self.create_serializer()

        # Normal updates
        self.assertDictEqual(serializer.include_extra_kwargs({'a': 0}, {'a': 1}), {'a': 1})
        self.assertDictEqual(serializer.include_extra_kwargs({'a': 0}, {'b': 1}), {'a': 0, 'b': 1})

        # Special cases
        self.assertDictEqual(serializer.include_extra_kwargs({'min_length': 3}, {'read_only': True}),
                             {'read_only': True})
        self.assertDictEqual(serializer.include_extra_kwargs({'required': False}, {'default': 1}),
                             {'default': 1})
        self.assertDictEqual(serializer.include_extra_kwargs({'read_only': True}, {'required': True}),
                             {'read_only': True})
        self.assertDictEqual(serializer.include_extra_kwargs({}, {'child_kwargs': {}}),
                             {})

    def test_get_extra_kwargs(self):
        def get(extra_kwargs=None, read_only_fields=None):
            meta = {'extra_kwargs': extra_kwargs, 'read_only_fields': read_only_fields}
            return self.create_serializer(meta=meta).get_extra_kwargs()

        self.assertDictEqual(get(extra_kwargs={'name': {'max_length': 20}}),
                             {'name': {'max_length': 20}})
        self.assertDictEqual(get(extra_kwargs={'name': {'max_length': 20}}, read_only_fields=['name']),
                             {'name': {'max_length': 20, 'read_only': True}})

        with self.assertRaises(TypeError):
            get(read_only_fields='invalid')

        with self.assertRaises(AssertionError):
            self.create_serializer(meta={'readonly_fields': ['name']}).get_extra_kwargs()

    def test_to_internal_representation(self):
        ser = self.create_serializer(Person)

        # simple
        value = ser.to_internal_value({'name': 'Alice', 'length': 123, 'birth_date': '2020-02-02'})
        self.assertEqual(value, Person(name='Alice', length=123, birth_date=datetime.date(2020, 2, 2)))
        self.assertEqual(value._unsupplied_fields, [])

        # unsupplied fields
        value = ser.to_internal_value({'name': 'Alice', 'length': 123})
        self.assertEqual(value, Person(name='Alice', length=123))
        self.assertEqual(value._unsupplied_fields, ["birth_date"])

        # nested
        simple = dataclasses.make_dataclass('child', [('value', str)])
        parent = dataclasses.make_dataclass('parent', [('container', simple)])
        self.assertEqual(self.create_serializer(parent).to_internal_value({'container': {'value': 'a'}}),
                         parent(container=simple(value='a')))