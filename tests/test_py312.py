import typing
import unittest
import sys

from rest_framework_dataclasses import typing_utils


@unittest.skipIf(sys.version_info < (3, 12, 0), 'Python 3.12 required')
class Python312Test(unittest.TestCase):
    def test_resolve_pep695(self):
        type Str = str
        type StrList = list[str]
        type GenericList[T] = list[T]

        class Hinted:
            a: Str
            b: StrList
            c: GenericList

        hints = typing_utils.get_resolved_type_hints(Hinted)
        self.assertEqual(hints['a'], str)
        self.assertEqual(hints['b'], list[str])
        self.assertEqual(typing.get_origin(hints['c']), list)

    def test_typevar_pep695(self):
        type GenericList[T: str] = list[T]
        def fn() -> GenericList:
            pass

        tp = typing_utils.get_resolved_type_hints(fn)['return']

        self.assertTrue(typing_utils.is_iterable_type(tp))
        element_type = typing_utils.get_iterable_element_type(tp)
        self.assertTrue(typing_utils.is_type_variable(element_type))
        self.assertEqual(typing_utils.get_type_variable_substitution(element_type), str)
