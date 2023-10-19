import unittest
import sys


def load_tests(loader: unittest.TestLoader, tests, pattern):
    # Manually load tests to avoid loading tests with syntax that's incompatible with the current Python version
    for module in (
        'test_field_generation',
        'test_field_utils',
        'test_fields',
        'test_functional',
        'test_issues',
        'test_serializers',
        'test_typing_utils',
    ):
        tests.addTests(loader.loadTestsFromName('tests.' + module))

    if sys.version_info >= (3, 12, 0):
        tests.addTests(loader.loadTestsFromName('tests.test_py312'))

    return tests
