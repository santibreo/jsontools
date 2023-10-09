from __future__ import annotations

from copy import deepcopy
from unittest import TestCase

import jsontools
import pytest

TEST_JSON = {
    'a': 1,
    'b': {
        'b-a': 1,
        'b-b': {'b-b-a': 1, 'b-b-b': 2, 'b-b-c': [1, 2, 3]},
        'b-c': [{'b-c-a': 1}, {'b-c-a': 2}],
    },
    'c': [
        {'c-a': 1},
        {'c-a': 2},
        {'c-b': 2},
        {'c-c': {'c-c-a': 1, 'c-c-b': 2, 'c-c-c': [1, 2, 3]}},
    ],
}


class TestJsonTools(TestCase):
    def setUp(self) -> None:
        self.expected: list = []
        self.test_json = deepcopy(TEST_JSON)
        self.test_nc_json = {
            'hello_world': {
                'hello_world': [
                    {'hello_world': 1},
                    {'hello_world': 2},
                    {'hello_world': 3},
                ],
            },
        }


@pytest.fixture
def test_case() -> TestCase:
    test_case_inst = TestJsonTools()
    test_case_inst.setUp()
    return test_case_inst


def test_flatten(test_case):
    expected = [
        ('a', test_case.test_json['a']),
        ('b', test_case.test_json['b']),
        ('b/b-a', test_case.test_json['b']['b-a']),
        ('b/b-b', test_case.test_json['b']['b-b']),
        ('b/b-b/b-b-a', test_case.test_json['b']['b-b']['b-b-a']),
        ('b/b-b/b-b-b', test_case.test_json['b']['b-b']['b-b-b']),
        ('b/b-b/b-b-c', test_case.test_json['b']['b-b']['b-b-c']),
        ('b/b-c', test_case.test_json['b']['b-c']),
        ('b/b-c[0]/b-c-a', test_case.test_json['b']['b-c'][0]['b-c-a']),
        ('b/b-c[1]/b-c-a', test_case.test_json['b']['b-c'][1]['b-c-a']),
        ('c', test_case.test_json['c']),
        ('c[0]/c-a', test_case.test_json['c'][0]['c-a']),
        ('c[1]/c-a', test_case.test_json['c'][1]['c-a']),
        ('c[2]/c-b', test_case.test_json['c'][2]['c-b']),
        ('c[3]/c-c', test_case.test_json['c'][3]['c-c']),
        ('c[3]/c-c/c-c-a', test_case.test_json['c'][3]['c-c']['c-c-a']),
        ('c[3]/c-c/c-c-b', test_case.test_json['c'][3]['c-c']['c-c-b']),
        ('c[3]/c-c/c-c-c', test_case.test_json['c'][3]['c-c']['c-c-c']),
    ]
    result = list(jsontools.flatten(test_case.test_json))
    test_case.assertListEqual(result, expected)


@pytest.mark.parametrize(
    'max_depth,expected_slices',
    [
        (-1, [slice(None)]),
        (0, [slice(0, 1)]),
        (1, [slice(0, 2), slice(5, 9)]),
        (2, [slice(None)]),
    ],
)
def test_walk_structures(max_depth, expected_slices, test_case):
    expected_full = [
        test_case.test_json,
        test_case.test_json['b'],
        test_case.test_json['b']['b-b'],
        test_case.test_json['b']['b-c'][0],
        test_case.test_json['b']['b-c'][1],
        test_case.test_json['c'][0],
        test_case.test_json['c'][1],
        test_case.test_json['c'][2],
        test_case.test_json['c'][3],
        test_case.test_json['c'][3]['c-c'],
    ]
    expected = []
    for slice_ in expected_slices:
        expected.extend(expected_full[slice_])
    result = list(jsontools.walk_structures(test_case.test_json, max_depth=max_depth))
    test_case.assertListEqual(result, expected)


@pytest.mark.parametrize(
    'key_pattern,expected',
    [
        ('-', []),
        ('a', [('a', 1)]),
        ('b/b-a', [('b/b-a', 1)]),
        ('b/.*/b-b-a', [('b/b-b/b-b-a', 1)]),
        ('b-c/b-c-a', []),
        (r'.*/b-c\[\d\]/b-c-a', [('b/b-c[0]/b-c-a', 1), ('b/b-c[1]/b-c-a', 2)]),
        (r'[^/]\[\d\]/(c-a)', [('c-a', 1), ('c-a', 2)]),
        ('.*/(c-c-c)', [('c-c-c', [1, 2, 3])]),
        ('.*/(?:c-c-c)', [('c[3]/c-c/c-c-c', [1, 2, 3])]),
    ],
)
def test_query_keys(key_pattern, expected, test_case):
    result = list(jsontools.query_keys(test_case.test_json, key_pattern))
    test_case.assertListEqual(result, expected)


@pytest.mark.parametrize(
    'key_pattern,expected',
    [
        ('A', []),
        ('a', [TEST_JSON]),
        ('b/b-a', [TEST_JSON]),
        ('b-c-a', TEST_JSON['b']['b-c']),
        ('c-.', TEST_JSON['c']),
        ('c-[a-b]', TEST_JSON['c'][:3]),
        (r'b-c\[\d\]/b-c-a', [TEST_JSON['b']]),
    ],
)
def test_search_by_keys_single(key_pattern, expected, test_case):
    result = list(jsontools.search_by_keys(test_case.test_json, key_pattern))
    test_case.assertListEqual(result, expected)


@pytest.mark.parametrize(
    'key_patterns,expected',
    [
        (('A',), []),
        (('a',), [TEST_JSON]),
        (('a', 'd'), []),
        (('b-a', 'b-b', 'b-c'), [TEST_JSON['b']]),
        (('b-a', 'b-b', 'b-c', 'b-d'), []),
        (('b-[a-d]',), [TEST_JSON['b']]),
        (('c-a', 'c-b', 'c-c'), []),
        (('c-[a-b]',), TEST_JSON['c'][:3]),
        (('c-[a-c]',), TEST_JSON['c']),
    ],
)
def test_search_by_keys_multiple(key_patterns, expected, test_case: TestJsonTools):
    result = list(
        jsontools.search_by_keys(test_case.test_json, *key_patterns, all_=True),
    )
    test_case.assertListEqual(result, expected)


def test_json_edit(test_case: TestJsonTools):
    def matcher(k: str, _):
        return k == 'c-a'

    def converter(k: str, v: jsontools.JsonValue):
        assert isinstance(v, int), f'Value of key {k} is {v}, not an integer'
        yield k, v + 1
        yield k + '-new', v + 2

    jsontools.edit(test_case.test_json, matcher, converter)
    test_case.assertEqual(test_case.test_json['c'][0]['c-a'], 2)
    test_case.assertEqual(test_case.test_json['c'][0]['c-a-new'], 3)
    test_case.assertEqual(test_case.test_json['c'][1]['c-a'], 3)
    test_case.assertEqual(test_case.test_json['c'][1]['c-a-new'], 4)


def test_json_edit_replace_with_and_without_drop(test_case: TestJsonTools):
    def matcher(k: str, _):
        return k == 'c-a'

    def converter(k: str, v: int):
        yield k, v + 1
        yield k + '-new', v + 2

    jsontools.edit(test_case.test_json, matcher, converter)
    without_drop = deepcopy(test_case.test_json)
    test_case.setUp()
    jsontools.edit(test_case.test_json, matcher, converter, drop=True)
    test_case.assertDictEqual(without_drop, test_case.test_json)


def test_apply_mapping_dict(test_case: TestJsonTools):
    mapping = {
        'b-a': lambda k, v: v + 1,
        'c-a': lambda k, v: v + 1,
        'c-c-c': lambda k, v: v + [4],
        'no-key': lambda k, v: ValueError('This should not be called'),
    }
    jsontools.apply_mapping(test_case.test_json, mapping)
    test_case.assertEqual(test_case.test_json['b']['b-a'], 2)
    test_case.assertEqual(test_case.test_json['c'][0]['c-a'], 2)
    test_case.assertEqual(test_case.test_json['c'][1]['c-a'], 3)
    test_case.assertEqual(test_case.test_json['c'][3]['c-c']['c-c-c'], [1, 2, 3, 4])


def test_apply_mapping_list(test_case: TestJsonTools):
    mapping = {
        'b-a': lambda k, v: v + 1,
        'c-a': lambda k, v: v + 1,
        'c-c-c': lambda k, v: v + [4],
        'no-key': lambda k, v: ValueError('This should not be called'),
    }
    jsontools.apply_mapping([test_case.test_json], mapping)
    test_case.assertEqual(test_case.test_json['b']['b-a'], 2)
    test_case.assertEqual(test_case.test_json['c'][0]['c-a'], 2)
    test_case.assertEqual(test_case.test_json['c'][1]['c-a'], 3)
    test_case.assertEqual(test_case.test_json['c'][3]['c-c']['c-c-c'], [1, 2, 3, 4])


@pytest.mark.parametrize(
    'orig_nc,dest_nc',
    [
        ('snake_case', 'CamelCase'),
        ('CamelCase', 'lowerCamelCase'),
        ('lowerCamelCase', 'Display Name'),
        ('Display Name', 'snake_case'),
    ],
)
def test_convert_keys_to_naming_convention(orig_nc, dest_nc, test_case: TestJsonTools):
    jsontools.convert_keys_to_naming_convention(
        test_case.test_nc_json,
        orig_nc,
        dest_nc,
    )
