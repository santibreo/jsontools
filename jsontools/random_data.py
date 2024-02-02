"""Tools to create random Python builtin objects."""
from __future__ import annotations

import zoneinfo
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from functools import partial
from random import choice
from random import choices
from random import randint
from random import random as randfloat
from string import ascii_letters
from types import NoneType
from typing import Callable


MAX_LEVEL_DEPTH = 4
'Maximum nesting level of complex types'
VALID_TIMEZONES = list(zoneinfo.available_timezones())
'List of timezone names'
DATETIME_MINIMUM = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
'The minimum value for a valid date'
randstr = lambda: ''.join(choices(ascii_letters + '_-', k=randint(4, 12)))
"Returns a random string of ascii letters, '_' and '-'"
randtimezone = lambda: zoneinfo.ZoneInfo(choice(VALID_TIMEZONES))
'Returns a random :class:`zoneinfo.ZoneInfo`'
randdatetime = lambda: (
    (
        DATETIME_MINIMUM + timedelta(seconds=randint(0, 3600 * 24 * 365 * 100))
    ).astimezone(randtimezone())
)
'Returns a random datetime after :class:`DATETIME_MINIMUM`'
SIMPLE_TYPES = (str, int, float, datetime, NoneType)
'Default types that are not collections (string included)'
COMPLEX_TYPES = (list, dict)
'Types that are collections (string excluded)'
_RANDOM_FUNC_BY_TYPE: dict[type, Callable] = {
    str: randstr,
    int: partial(randint, 1, 101),
    float: randfloat,
    datetime: randdatetime,
    NoneType: lambda: None,
}
'Mapping between each builtin Python type and its random generator'


def randtypes(level: int = 1, n: int = 1) -> list[type]:
    R"""Returns a random type from :class:`RANDOM_FUNC_BY_TYPE`

    Args:
        level: Controls how likely it is to get a complex type. Higher values
            make it more unlikely. Values over :class:`MAX_LEVEL_DEPTH` returns
            always :class:`SIMPLE_TYPES`.

    Return:
        A list of ``type``\ s from :class:`RANDOM_FUNC_BY_TYPE`.

    """
    level, n = max(level, 1), max(n, 1)
    w_complex = (0.1 / len(COMPLEX_TYPES)) / level if level < MAX_LEVEL_DEPTH else 0
    w_simple = (1 - (w_complex * len(COMPLEX_TYPES))) / len(SIMPLE_TYPES)
    weights = [w_simple] * len(SIMPLE_TYPES) + [w_complex] * len(COMPLEX_TYPES)
    return choices(SIMPLE_TYPES + COMPLEX_TYPES, weights, k=n)


def randlist(
    value_type: type | None = None,
    total_items: int = 10,
    level: int = 1,
):
    """Createss a list that contains ``total_items`` random items, all of the same
    type.

    Args:
        value_type: One of the types in :class:`RANDOM_FUNC_BY_TYPE`. Defines
            the type of the objects inside the list. If not given a random
            type is selected
        total_items: Total number of items in the list. Defaults to 10.
        level: Controls how likely it is to get a complex type. Higher values
            make it more unlikely. Values over :class:`MAX_LEVEL_DEPTH` returns
            always :class:`SIMPLE_TYPES`.

    Return:
        A list filled with random items.

    """
    result = []
    value_type = value_type or randtypes(level, 1)[0]
    value_func = _RANDOM_FUNC_BY_TYPE[value_type]
    if value_type is list or value_type is dict:
        value_func = partial(value_func, level=level + 1)
    for _ in range(total_items):
        result.append(value_func())
    return result


def randdict(
    list_value_type: type | None = None,
    total_items: int = 10,
    level: int = 1,
):
    R"""Dict that contains random items, but all keys are :class:`str`

    Args:
        list_value_type: Type of items for :class:`list`\ s. If not given, it
            can be any from :class:`RANDOM_FUNC_BY_TYPE`.
        total_items: Number of items in the :class:`dict` without considering
            nesting.
        level: Controls how likely it is to get a complex type. Higher values
            make it more unlikely. Values over :class:`MAX_LEVEL_DEPTH` returns
            always :class:`SIMPLE_TYPES`. It increases automatically for nested
            ``dict``\ s and ``list``\ s.

    Return:
        A ``dict`` filled with random items .

    """
    result = dict.fromkeys(randstr() for _ in range(total_items))
    value_types = randtypes(level=level, n=total_items)
    for key, val_type in zip(result, value_types):
        if val_type is dict:
            result[key] = randdict(level=level + 1)
        if val_type is list:
            result[key] = randlist(
                value_type=list_value_type or val_type,
                level=level + 1,
            )
        else:
            result[key] = _RANDOM_FUNC_BY_TYPE[val_type]()
    return result


_RANDOM_FUNC_BY_TYPE[list] = randlist
_RANDOM_FUNC_BY_TYPE[dict] = randdict
