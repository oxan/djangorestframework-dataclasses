import typing

from unittest import TestCase, SkipTest

from rest_framework_dataclasses import typing_utils


class TypingTest(TestCase):
    def test_iterable(self):
        self.assertTrue(typing_utils.is_iterable_type(typing.Iterable[str]))
        self.assertTrue(typing_utils.is_iterable_type(typing.Collection[str]))
        self.assertTrue(typing_utils.is_iterable_type(typing.Mapping[str, int]))
        self.assertTrue(typing_utils.is_iterable_type(typing.Sequence[str]))
        self.assertTrue(typing_utils.is_iterable_type(typing.List[str]))
        self.assertTrue(typing_utils.is_iterable_type(typing.Dict[str, int]))
        self.assertTrue(typing_utils.is_iterable_type(typing.Set[str]))
        self.assertTrue(typing_utils.is_iterable_type(typing.Generator[str, int, int]))
        self.assertFalse(typing_utils.is_iterable_type(str))
        self.assertFalse(typing_utils.is_iterable_type(bytes))
        self.assertFalse(typing_utils.is_iterable_type(int))
        self.assertFalse(typing_utils.is_iterable_type(TypingTest))

        self.assertEqual(typing_utils.get_iterable_element_type(typing.Iterable[str]), str)
        self.assertEqual(typing_utils.get_iterable_element_type(typing.Collection[str]), str)
        self.assertEqual(typing_utils.get_iterable_element_type(typing.Mapping[str, int]), str)
        self.assertEqual(typing_utils.get_iterable_element_type(typing.Sequence[str]), str)
        self.assertEqual(typing_utils.get_iterable_element_type(typing.List[str]), str)
        self.assertEqual(typing_utils.get_iterable_element_type(typing.Dict[str, int]), str)
        self.assertEqual(typing_utils.get_iterable_element_type(typing.Set[str]), str)
        self.assertEqual(typing_utils.get_iterable_element_type(typing.Generator[str, int, int]), str)

        with self.assertRaises(ValueError):
            typing_utils.get_iterable_element_type(str)

    def test_mapping(self):
        self.assertTrue(typing_utils.is_mapping_type(typing.Mapping[str, int]))
        self.assertTrue(typing_utils.is_mapping_type(typing.Dict[str, int]))
        self.assertFalse(typing_utils.is_mapping_type(str))
        self.assertFalse(typing_utils.is_mapping_type(int))
        self.assertFalse(typing_utils.is_mapping_type(TypingTest))

        self.assertEqual(typing_utils.get_mapping_value_type(typing.Mapping[str, int]), int)
        self.assertEqual(typing_utils.get_mapping_value_type(typing.Dict[str, int]), int)

        with self.assertRaises(ValueError):
            typing_utils.get_mapping_value_type(str)

    def test_optional(self):
        self.assertTrue(typing_utils.is_optional_type(typing.Optional[str]))
        self.assertTrue(typing_utils.is_optional_type(typing.Union[str, None]))
        self.assertTrue(typing_utils.is_optional_type(typing.Union[str, typing.Optional[str]]))
        self.assertTrue(typing_utils.is_optional_type(typing.Union[str, typing.Union[str, None]]))
        self.assertFalse(typing_utils.is_optional_type(str))
        self.assertFalse(typing_utils.is_optional_type(int))
        self.assertFalse(typing_utils.is_optional_type(TypingTest))

        self.assertEqual(typing_utils.get_optional_type(typing.Optional[str]), str)
        self.assertEqual(typing_utils.get_optional_type(typing.Union[str, None]), str)
        self.assertEqual(typing_utils.get_optional_type(typing.Union[str, typing.Optional[str]]), str)
        self.assertEqual(typing_utils.get_optional_type(typing.Union[str, typing.Union[str, None]]), str)

        with self.assertRaises(ValueError):
            typing_utils.get_optional_type(str)

    def test_literal_nested(self):
        try:
            from typing import Literal
        except ImportError:
            raise SkipTest("typing.Literal not supported on current Python")

        self.assertEqual(typing_utils.get_literal_choices(Literal[Literal[Literal[1, 2, 3], "foo"], 5, None]),
                         [1, 2, 3, "foo", 5, None])

    # Make sure we recognize Literal from both 'typing' and 'typing_extensions'
    def test_literal_py38(self):
        try:
            from typing import Literal
        except ImportError:
            raise SkipTest("typing.Literal not supported on current Python")

        self.assertTrue(typing_utils.is_literal_type(Literal['a']))
        self.assertEqual(typing_utils.get_literal_choices(Literal['a', 'b', None]),
                         ['a', 'b', None])

    def test_literal_extensions(self):
        try:
            from typing_extensions import Literal
        except ImportError:
            raise SkipTest("typing_extensions module not installed")

        self.assertTrue(typing_utils.is_literal_type(Literal['a']))
        self.assertEqual(typing_utils.get_literal_choices(Literal['a', 'b', None]),
                         ['a', 'b', None])
