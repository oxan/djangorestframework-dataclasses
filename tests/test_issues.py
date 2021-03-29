import dataclasses
import typing

from unittest import TestCase

from rest_framework import fields
from rest_framework_dataclasses.serializers import DataclassSerializer


@dataclasses.dataclass
class Simple:
    value: str


class SimpleSerializer(DataclassSerializer):
    class Meta:
        dataclass = Simple


class IssuesTest(TestCase):
    def check_deserialize(self, serializer=DataclassSerializer, **kwargs):
        serializer = serializer(**kwargs)
        serializer.is_valid(raise_exception=True)
        serializer.save()

    # Issue #3: save() with nested dataclasses is broken
    def test_save_nested_dataclass(self):
        parent = dataclasses.make_dataclass('Parent', [('nested', Simple)])
        data = {'nested': {'value': 'A'}}

        self.check_deserialize(dataclass=parent, data=data)

    # Issue #13: save() with nested list items is broken
    def test_nested_list(self):
        parent = dataclasses.make_dataclass('Parent', [('nested', typing.List[Simple])])
        data = {'nested': [{'value': 'A'}]}

        class ParentSerializer(DataclassSerializer):
            nested = SimpleSerializer(many=True)

        self.check_deserialize(ParentSerializer, dataclass=parent, data=data)

    # Issue #15: save() with nullable nested is broken
    def test_nested_nullable(self):
        parent = dataclasses.make_dataclass('Parent', [('nested', typing.Optional[Simple])])
        data = {'nested': None}

        class ParentSerializer(DataclassSerializer):
            nested = SimpleSerializer(allow_null=True, required=False)

        self.check_deserialize(ParentSerializer, dataclass=parent, data=data)

    # Issue #19: create() breaks with source parameter
    def test_create_source(self):
        data = {'renamed_value': 'a'}

        class SimpleRenamedSerializer(DataclassSerializer):
            renamed_value = fields.CharField(source='value')

            class Meta:
                dataclass = Simple
                fields = ('renamed_value', )

        self.check_deserialize(SimpleRenamedSerializer, data=data)

    # Issue #39: many=True results in empty sentinel in validated_data for optional fields
    def test_many_empty(self):
        @dataclasses.dataclass
        class HelloWorld:
            value: str = 'default'

        serializer = DataclassSerializer(dataclass=HelloWorld, many=True, data=[{}])
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        self.assertIsNot(fields.empty, data[0].value)
        self.assertEqual('default', data[0].value)
