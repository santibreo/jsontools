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
from random import random
from random import seed
from string import ascii_letters
from types import NoneType
from typing import Callable


VALID_TIMEZONES = list(zoneinfo.available_timezones())
'List of timezone names'
DATETIME_MINIMUM = datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
'The minimum value for a valid date'
random_float = random
'Returns a random float between 0 and 1'
random_integer = lambda: randint(1, 101)
'Returns a random integer between 1 and 100'
random_string = lambda: ''.join(choices(ascii_letters + '_-', k=randint(4, 12)))
"Returns a random string of ascii letters, '_' and '-'"
random_timezone = lambda: zoneinfo.ZoneInfo(choice(VALID_TIMEZONES))
'Returns a random :class:`zoneinfo.ZoneInfo`'
random_datetime = lambda: (
    (
        DATETIME_MINIMUM + timedelta(seconds=randint(0, 3600 * 24 * 365 * 100))
    ).astimezone(random_timezone())
)
'Returns a random datetime after :class:`DATETIME_MINIMUM`'
SIMPLE_TYPES = (str, int, float, datetime, NoneType)
'Default types that are not collections (string included)'
COMPLEX_TYPES = (list, dict)
'Types that are collections (string excluded)'
RANDOM_FUNC_BY_TYPE: dict[type, Callable] = {
    str: random_string,
    int: random_integer,
    float: random_float,
    datetime: random_datetime,
    NoneType: lambda: None,
}
'Mapping between each builtin Python type and its random generator'


class RandomList(list):
    """List that contains random items, all of the same type."""

    def __init__(
        self,
        value_type: type | None = None,
        total_items: int = 10,
        level: int = 1,
    ):
        w_complex = (0.1 / len(COMPLEX_TYPES)) / level if level < 4 else 0
        w_simple = (1 - (w_complex * len(COMPLEX_TYPES))) / len(SIMPLE_TYPES)
        weights = [w_simple] * len(SIMPLE_TYPES) + [w_complex] * len(COMPLEX_TYPES)
        other_value_type = choices(SIMPLE_TYPES + COMPLEX_TYPES, weights, k=1)[0]
        value_type = value_type or other_value_type
        value_func = RANDOM_FUNC_BY_TYPE[value_type]
        if value_type is list or value_type is dict:
            value_func = partial(value_func, level=level + 1)
        for _ in range(total_items):
            self.append(value_func())


class RandomDict(dict):
    """Dict that contains random items, but all keys are :class:`str`"""

    def __init__(
        self,
        list_value_type: type | None = None,
        total_items: int = 10,
        level: int = 1,
    ):
        keys = (random_string() for _ in range(total_items))
        w_complex = (0.1 / len(COMPLEX_TYPES)) / level if level < 4 else 0
        w_simple = (1 - (w_complex * len(COMPLEX_TYPES))) / len(SIMPLE_TYPES)
        weights = [w_simple] * len(SIMPLE_TYPES) + [w_complex] * len(COMPLEX_TYPES)
        value_types = choices(SIMPLE_TYPES + COMPLEX_TYPES, weights, k=total_items)
        for key, val_type in zip(keys, value_types):
            if val_type is dict:
                self[key] = RandomDict(level=level + 1)
            if val_type is list:
                self[key] = RandomList(value_type=list_value_type, level=level + 1)
            else:
                self[key] = RANDOM_FUNC_BY_TYPE[val_type]()


RANDOM_FUNC_BY_TYPE[list] = RandomList
RANDOM_FUNC_BY_TYPE[dict] = RandomDict


if __name__ == '__main__':
    seed(1122)
    RandomDict()
