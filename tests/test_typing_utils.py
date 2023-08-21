import typing
import unittest
import sys

from rest_framework_dataclasses import types, typing_utils


class TypingTest(unittest.TestCase):
    def assertAnyTypeEquivalent(self, tp: type):
        # In some cases we accept either typing.Any (used by Python 3.9+) or an unconstrained typevar (used by Python
        # 3.7 and 3.8). It's essentially the same, and we strip the typevar before usage anyway.
        self.assertTrue(tp is typing.Any or (isinstance(tp, typing.TypeVar) and len(tp.__constraints__) == 0))

    def test_iterable(self):
        self.assertTrue(typing_utils.is_iterable_type(typing.Iterable[str]))
        self.assertTrue(typing_utils.is_iterable_type(typing.Collection[str]))
        self.assertTrue(typing_utils.is_iterable_type(typing.Mapping[str, int]))
        self.assertTrue(typing_utils.is_iterable_type(typing.Sequence[str]))
        self.assertTrue(typing_utils.is_iterable_type(typing.List[str]))
        self.assertTrue(typing_utils.is_iterable_type(typing.Dict[str, int]))
        self.assertTrue(typing_utils.is_iterable_type(typing.Set[str]))
        self.assertTrue(typing_utils.is_iterable_type(typing.Generator[str, int, int]))
        self.assertTrue(typing_utils.is_iterable_type(typing.List))
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
        self.assertAnyTypeEquivalent(typing_utils.get_iterable_element_type(typing.List))

        with self.assertRaises(ValueError):
            typing_utils.get_iterable_element_type(str)

    def test_mapping(self):
        self.assertTrue(typing_utils.is_mapping_type(typing.Mapping[str, int]))
        self.assertTrue(typing_utils.is_mapping_type(typing.Dict[str, int]))
        self.assertTrue(typing_utils.is_mapping_type(typing.Dict))
        self.assertFalse(typing_utils.is_mapping_type(str))
        self.assertFalse(typing_utils.is_mapping_type(int))
        self.assertFalse(typing_utils.is_mapping_type(TypingTest))

        self.assertEqual(typing_utils.get_mapping_value_type(typing.Mapping[str, int]), int)
        self.assertEqual(typing_utils.get_mapping_value_type(typing.Dict[str, int]), int)
        self.assertAnyTypeEquivalent(typing_utils.get_mapping_value_type(typing.Dict))

        with self.assertRaises(ValueError):
            typing_utils.get_mapping_value_type(str)

    @unittest.skipIf(sys.version_info < (3, 9, 0), 'Python 3.9 required')
    def test_pep585(self):
        self.assertTrue(typing_utils.is_iterable_type(list[int]))
        self.assertEqual(typing_utils.get_iterable_element_type(list[int]), int)

        self.assertTrue(typing_utils.is_mapping_type(dict[str, int]))
        self.assertTrue(typing_utils.get_mapping_value_type(dict[str, int]), int)

    def test_optional(self):
        self.assertTrue(typing_utils.is_optional_type(typing.Optional[str]))
        self.assertTrue(typing_utils.is_optional_type(typing.Union[str, None]))
        self.assertTrue(typing_utils.is_optional_type(typing.Union[str, typing.Optional[str]]))
        self.assertTrue(typing_utils.is_optional_type(typing.Union[str, typing.Union[str, None]]))
        self.assertTrue(typing_utils.is_optional_type(typing.Union[str, int, None]))
        self.assertFalse(typing_utils.is_optional_type(str))
        self.assertFalse(typing_utils.is_optional_type(int))
        self.assertFalse(typing_utils.is_optional_type(TypingTest))

        self.assertEqual(typing_utils.get_optional_type(typing.Optional[str]), str)
        self.assertEqual(typing_utils.get_optional_type(typing.Union[str, None]), str)
        self.assertEqual(typing_utils.get_optional_type(typing.Union[None, str]), str)
        self.assertEqual(typing_utils.get_optional_type(typing.Union[str, typing.Optional[str]]), str)
        self.assertEqual(typing_utils.get_optional_type(typing.Union[str, typing.Union[str, None]]), str)
        self.assertEqual(typing_utils.get_optional_type(typing.Union[str, int, None]), typing.Union[str, int])

        with self.assertRaises(ValueError):
            typing_utils.get_optional_type(str)

    @unittest.skipIf(sys.version_info < (3, 10, 0), 'Python 3.10 required')
    def test_optional_pep604(self):
        # New PEP 604 union syntax in Python 3.10+
        self.assertTrue(typing_utils.is_optional_type(str | None))
        self.assertTrue(typing_utils.is_optional_type(None | str))
        self.assertTrue(typing_utils.is_optional_type(str | int | None))

        self.assertEqual(typing_utils.get_optional_type(str | None), str)
        self.assertEqual(typing_utils.get_optional_type(None | str), str)
        self.assertEqual(typing_utils.get_optional_type(str | int | None), str | int)

        self.assertFalse(typing_utils.is_optional_type(int | str))

    def test_union(self):
        self.assertTrue(typing_utils.is_union_type(typing.Union[str, int]))
        self.assertTrue(typing_utils.is_union_type(typing.Union[str, int, float]))
        self.assertFalse(typing_utils.is_union_type(typing.Union[str]))
        self.assertFalse(typing_utils.is_union_type(typing.Union[str, None]))
        self.assertFalse(typing_utils.is_union_type(typing.Optional[str]))

        self.assertEqual(typing_utils.get_union_choices(typing.Union[str, int]), [str, int])
        self.assertEqual(typing_utils.get_union_choices(typing.Union[str, int, float]), [str, int, float])

        with self.assertRaises(ValueError):
            typing_utils.get_union_choices(str)

    @unittest.skipIf(sys.version_info < (3, 10, 0), 'Python 3.10 required')
    def test_union_pep604(self):
        self.assertTrue(typing_utils.is_union_type(str | int))
        self.assertTrue(typing_utils.is_union_type(str | int | float))
        self.assertFalse(typing_utils.is_union_type(str | None))

        self.assertEqual(typing_utils.get_union_choices(str | int), [str, int])
        self.assertEqual(typing_utils.get_union_choices(str | int | float), [str, int, float])

    def test_final(self):
        self.assertTrue(typing_utils.is_final_type(types.Final[int]))
        self.assertTrue(typing_utils.is_final_type(types.Final))
        self.assertFalse(typing_utils.is_final_type(int))

        self.assertEqual(typing_utils.get_final_type(types.Final[int]), int)
        self.assertAnyTypeEquivalent(typing_utils.get_final_type(types.Final))

        with self.assertRaises(ValueError):
            typing_utils.get_final_type(str)

    def test_literal(self):
        self.assertTrue(typing_utils.is_literal_type(types.Literal['a', 'b']))
        self.assertTrue(typing_utils.is_literal_type(types.Literal['a', 'b', None]))
        self.assertTrue(typing_utils.is_literal_type(types.Literal['a', 'b', types.Literal['c', 'd']]))
        self.assertTrue(typing_utils.is_literal_type(types.Literal['a', 'b', types.Literal['c', 'd', None]]))
        self.assertTrue(typing_utils.is_literal_type(types.Literal['a', 'b', types.Literal[1, 2]]))
        self.assertTrue(typing_utils.is_literal_type(types.Literal['a', 'b', types.Literal[1, 2, None]]))

        self.assertFalse(typing_utils.is_optional_type(types.Literal['a', 'b']))
        self.assertTrue(typing_utils.is_optional_type(types.Literal['a', 'b', None]))
        self.assertFalse(typing_utils.is_optional_type(types.Literal['a', 'b', types.Literal['c', 'd']]))
        self.assertTrue(typing_utils.is_optional_type(types.Literal['a', 'b', types.Literal['c', 'd', None]]))
        self.assertFalse(typing_utils.is_optional_type(types.Literal['a', 'b', types.Literal[1, 2]]))
        self.assertTrue(typing_utils.is_optional_type(types.Literal['a', 'b', types.Literal[1, 2, None]]))

        self.assertListEqual(typing_utils.get_literal_choices(types.Literal['a', 'b']), ['a', 'b'])
        self.assertListEqual(typing_utils.get_literal_choices(types.Literal['a', 'b', None]), ['a', 'b', None])
        self.assertListEqual(typing_utils.get_literal_choices(types.Literal['a', 'b', types.Literal['c', 'd']]),
                             ['a', 'b', 'c', 'd'])
        self.assertListEqual(typing_utils.get_literal_choices(types.Literal['a', 'b', types.Literal['c', 'd', None]]),
                             ['a', 'b', 'c', 'd', None])
        self.assertListEqual(typing_utils.get_literal_choices(types.Literal['a', 'b', types.Literal[1, 2]]),
                             ['a', 'b', 1, 2])
        self.assertListEqual(typing_utils.get_literal_choices(types.Literal['a', 'b', types.Literal[1, 2, None]]),
                             ['a', 'b', 1, 2, None])

        with self.assertRaises(ValueError):
            typing_utils.get_literal_choices(str)

    # noinspection PyPep8Naming
    def test_variable_type(self):
        T = typing.TypeVar('T')
        U = typing.TypeVar('U', int, str)
        V = typing.TypeVar('V', bound=Exception)

        self.assertTrue(typing_utils.is_type_variable(T))
        self.assertTrue(typing_utils.is_type_variable(U))
        self.assertTrue(typing_utils.is_type_variable(V))
        self.assertFalse(typing_utils.is_type_variable(int))
        self.assertFalse(typing_utils.is_type_variable(typing.List))

        self.assertEqual(typing_utils.get_variable_type_substitute(T), typing.Any)
        self.assertEqual(typing_utils.get_variable_type_substitute(U), typing.Union[int, str])
        self.assertEqual(typing_utils.get_variable_type_substitute(V), Exception)
