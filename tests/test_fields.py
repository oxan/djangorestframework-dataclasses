import enum

from unittest import TestCase

from rest_framework.exceptions import ValidationError

from rest_framework_dataclasses.fields import DefaultDecimalField, EnumField


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
