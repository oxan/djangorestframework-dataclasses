import unittest
import typing

from rest_framework_dataclasses import field_utils
from rest_framework_dataclasses.types import Literal


class FieldUtilsTest(unittest.TestCase):
    def test_lookup_type(self):
        mapping = {
            str: 1,
            int: 2,
            typing.Union[int, str]: 3
        }

        self.assertEqual(field_utils.lookup_type_in_mapping(mapping, str), 1)
        self.assertEqual(field_utils.lookup_type_in_mapping(mapping, int), 2)
        self.assertEqual(field_utils.lookup_type_in_mapping(mapping, typing.Union[int, str]), 3)

        self.assertEqual(field_utils.lookup_type_in_mapping(mapping, type('email', (str, ), {})), 1)

        with self.assertRaises(KeyError):
            field_utils.lookup_type_in_mapping(mapping, float)
        with self.assertRaises(KeyError):
            field_utils.lookup_type_in_mapping(mapping, Literal['a', 'b'])
