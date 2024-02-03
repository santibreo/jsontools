"""Module containing functions that simplifies interactions with data structured
as JSON.
"""
from __future__ import annotations

import re
from typing import final
from typing import overload
from functools import wraps
from typing import Union
from typing import Literal
from typing import TypeVar
from typing import Mapping
from typing import Callable
from typing import Iterator
from typing import Iterable
from typing import Optional


# Typing
Variant = TypeVar('Variant')
Scalar = Union[int, float, bool, str, None]
"""Scalar types as they are present in JSON files."""
# Recursive types for JSONs
JsonContent = dict['JsonKey', 'JsonValue']
"""JSON content type."""
JsonKey = str
'JSON keys are always strings'
JsonValue = Union[Scalar, JsonContent, list[Scalar], list[JsonContent]]
'JSON values can be anything from JSON domain'
NamingConvention = Literal['CamelCase', 'lowerCamelCase', 'snake_case', 'Display Name']
'Valid naming convention names'
FLATTEN_PATH_END = re.compile(r'(?:\[(?P<index>\d+)\])?/?(?P<key>[^/\[\]]*)$')
'Regex pattern to decompose flatten JSON keys'


def decompose_flatten_path(flatten_path: str) -> tuple[str, Optional[int], str]:
    """Decomposes flatten path in:

    - ``prefix``: Path to the parent key if it is a ``list``. If not whole path.
    - ``key``: Last part of the path (key after '/')
    - ``index``: The index inside the  parent ``"[...]"`` if its value is part
       of a list

    .. see-also: :func:`flatten`

    Args:
        flatten_path: Path to identify JSON value

    Returns:
        3-Tuple with path ``prefix``, ``index`` and ``key``

    Examples:

        >>> decompose_flatten_path('c[3]')
        ('', 'c', 3)
        >>> decompose_flatten_path('c[3]/c-c/c-c-c')
        ('c[3]/c-c', 'c-c-c', None)

    """
    # Key and index
    search = FLATTEN_PATH_END.search(flatten_path)
    if not search:
        raise ValueError(f'Given path is not a flatten path: {flatten_path!r}')
    index, key = search.groups()
    if index is not None:
        index = int(index)
    # Prefix
    prefix = re.sub(FLATTEN_PATH_END, '', flatten_path)
    if index is None:
        prefix = f"{prefix + ('/' if prefix else '')}{key}"
    return prefix, index, key


def convert_name_to_naming_convention(
    name: str,
    orig_mode: NamingConvention = 'snake_case',
    dest_mode: NamingConvention = 'CamelCase',
) -> str:
    R"""Converts between different naming conventions. Currently supports:
    :class:`NamingConvention`.

    Args:
        name (str): Name to be converted
        orig_mode (Literal): Current naming convention of ``name`` (see
            supported ones). Defaults to 'snake_case'.
        dest_mode (Literal): Desired naming convention for ``name`` (see
            supported ones). Defaults to 'CamelCase'.

    Returns:
        str: Name converted to ``dest_mode`` naming convention

    Examples:

        >>> convert_name_to_naming_convention('hello_world')
        'HelloWorld'

        >>> convert_name_to_naming_convention('hello_world', dest_mode='lowerCamelCase')
        'helloWorld'

        >>> convert_name_to_naming_convention('hello_world', dest_mode='Display Name')
        'Hello World'

        >>> convert_name_to_naming_convention('HelloWorld', 'CamelCase', 'snake_case')
        'hello_world'

    """

    def remove_underline_and_uppercase_next_character(string: str) -> str:
        """Removes underlines and uppercase following character."""
        return_str: str = string
        pattern = re.compile(r'_\w')
        for match in re.finditer(pattern, string):
            return_str = re.sub(
                match.group(),
                match.group()[-1].upper(),
                return_str,
                count=1,
            )
        return return_str

    # Any name convention converted to snake_case
    if orig_mode == 'CamelCase':
        name_snake_case = re.sub(r'([A-Z])', r'_\1', name).strip()[1:].lower()
    elif orig_mode == 'lowerCamelCase':
        name_snake_case = re.sub(r'([A-Z])', r'_\1', name).strip().lower()
    elif orig_mode == 'Display Name':
        name_snake_case = name.strip().lower().replace(' ', '_')
    elif orig_mode == 'snake_case':
        name_snake_case = name.strip().lower()
    else:
        raise NotImplementedError(f'Unknown naming convention {orig_mode!r}')

    # From snake_case to destination naming convention
    if dest_mode == 'snake_case':
        return name_snake_case
    if dest_mode == 'CamelCase':
        return remove_underline_and_uppercase_next_character(
            name_snake_case.capitalize(),
        )
    if dest_mode == 'lowerCamelCase':
        return remove_underline_and_uppercase_next_character(name_snake_case)
    if dest_mode == 'Display Name':
        return name_snake_case.replace('_', ' ').title()
    raise NotImplementedError(f'Unknown naming convention {dest_mode!r}')


def one_or_many(
    func: Callable[[JsonContent, Variant], None],
) -> Callable[[JsonContent | list[JsonContent], Variant], None]:
    R"""Decorator to adap functions that modify a :class:`JsonContent` to allow
    them take also a list of :class:`JsonConfig`\ s.

    Args:
        func: Function that takes a :class:`JsonContent` as first argument and
            modifies it inplace.

    Returns:
        Function that can take either a :class:`JsonContent` or a list of
        :class:`JsonContent` as first argument. If it is a list, original
        function is applied to each item.

    """

    @wraps(func)
    def inner_func(
        json_content: JsonContent | list[JsonContent],
        *args,
        **kwargs,
    ):
        if not isinstance(json_content, (list, dict)):
            raise TypeError(f'Invalid JSON: {type(json_content)}')

        if isinstance(json_content, list):
            for json_item in json_content:
                func(json_item, *args, **kwargs)
        else:
            func(json_content, *args, **kwargs)

    return inner_func


def flatten(
    json_value: JsonValue,
    prefix: str = '',
) -> Iterator[tuple[JsonKey, JsonValue]]:
    R"""Traverses a nested JSON structure returning every key-value pair found,
    formatting keys by their path, from the shallowest to the deepest levels.

    Args:
        json_value: Any JSON structured content

    Yields:
        2-Tuples of path to key and its associated value

    """
    if isinstance(json_value, dict):
        for key, val in json_value.items():
            new_prefix = (f'{prefix}/' if prefix else '') + key
            yield new_prefix, val
            yield from flatten(val, prefix=new_prefix)
    elif isinstance(json_value, list):
        for i, inner_config in enumerate(json_value):
            new_prefix = prefix + f'[{i}]'
            yield from flatten(inner_config, prefix=new_prefix)


def unflatten(
    *path_val_pairs: tuple[str, JsonValue]
) -> JsonValue:
    R"""Recovers a nested JSON flattened structure.

    .. note::

        For consistency, this method takes the result of :func:`flatten` as
        input. Result type is defined by first element.

    Args:
        json_value: Any JSON structured content

    Yields:
        2-Tuples of path to key and its associated value

    """
    @overload
    def unflatten_(
        *path_val_pairs, is_list: Literal[True] = True
    ) -> Iterator[JsonValue | tuple[JsonKey, JsonContent]]: ...
    @overload
    def unflatten_(
        *path_val_pairs, is_list: Literal[False] = False
    ) -> Iterator[tuple[JsonKey, JsonContent]]: ...
    def unflatten_(
        *path_val_pairs, is_list: bool = False
    ) -> Iterator[JsonValue | tuple[JsonKey, JsonContent]]:
        (path, value), *remaining = path_val_pairs
        prefix, index, key = decompose_flatten_path(path)
        values = [{key: value}] if index is not None else []
        while remaining:
            (in_path, in_value), *remaining = remaining
            in_prefix, in_index, in_key = decompose_flatten_path(in_path)
            if not in_path.startswith(prefix):
                remaining = ((in_path, in_value), *remaining)
                break
            if in_index is None:
                continue
            # Populate list
            if in_index < len(values):
                values[in_index][in_key] = in_value
                continue
            values.append({in_key: in_value})

        if is_list:
            yield from values
        else:
            yield key, value

        if remaining:
            yield from unflatten_(*remaining)

    try:
        (path, _), *_ = path_val_pairs
    except ValueError:
        raise ValueError('There is nothing to unflat')
    _, index, _ = decompose_flatten_path(path)
    if index is None:
        return dict(unflatten_(*path_val_pairs, is_list=False))
    else:
        result = list()
        for value in unflatten_(*path_val_pairs, is_list=True):
            if isinstance(value, tuple):
                result.append({value[0]: value[1]})
            else:
                result.append(value)
        return result


def walk_structures(
    json_value: JsonValue,
    max_depth: int = -1,
) -> Iterator[JsonContent]:
    R"""Traverses a nested JSON file returning every dictionary found from
    shallowest to deepest levels.

    Args:
        json_value: JSON structured content
        max_depth: Maximun depth of the structure returned, each time a dictionary
            is scanned depth level is raised

    Yields:
        Each JSON structure found in the given JSON, including given,
        ``json_value`` at first place, one by one

    """

    def inner_walk_structures(
        json_value: JsonValue,
        current_depth: int = 0,
        max_depth: int = -1,
    ) -> Iterator[JsonContent]:
        if max_depth != -1 and current_depth > max_depth:
            return

        if isinstance(json_value, dict):
            yield json_value
            for json_value in json_value.values():
                yield from inner_walk_structures(
                    json_value,
                    current_depth=current_depth + 1,
                    max_depth=max_depth,
                )
        elif isinstance(json_value, list):
            for json_value in json_value:
                yield from inner_walk_structures(
                    json_value,
                    current_depth=current_depth,
                    max_depth=max_depth,
                )

    yield from inner_walk_structures(json_value, max_depth=max_depth)


def query_keys(
    json_content: JsonContent,
    key_pattern: str,
) -> Iterator[tuple[JsonKey, JsonValue]]:
    """Query JSON structured data looking for keys that match given ``key_pattern``
    as a `Python regexp <https://docs.python.org/3/library/re.html#regular-expression-syntax>`_

    - To separate nested fields '/' is used
    - To select listed items 0-indexed '[]' are used (only JSON items can be selected).

    .. note:
        To get only part of the matching flatten key (and not all) add a group to
        your pattern, last group is returned. If you need a group but do not want
        it as key, use non-capturing groups: '(?:...)'

    .. see-also: :func:`flatten`

    Args:
        json_content: JSON structured content
        key_pattern: Regexp compilable pattern

    Yields:
        Each pair of key and value that matches given ``key_pattern``.

    Raises:
        ValueError: If ``key_pattern`` cannot be interpreted as regexp pattern

    """
    try:
        re_pattern = re.compile(key_pattern)
    except re.error as error:
        raise ValueError(f"Invalid regexp pattern '{key_pattern}'") from error
    for key, value in flatten(json_content):
        if match := re.fullmatch(re_pattern, key):
            yield match.group(len(match.groups())), value


def search_by_keys(
    json_content: JsonContent,
    *key_patterns: str,
    all_: bool = False,
) -> Iterator[JsonContent]:
    R"""Looks recursively in a JSON file for JSON structures that contain given
    ``key_patterns``. If ``all_`` is ``True`` only internal structures that
    contain all ``key_patterns`` are returned.

    Args:
        json_content: JSON structured content
        \*key_patterns: Regexp patterns to search for in each JSON structure
        all_: If ``True`` only yields when all ``key_patterns`` have been found.
            Otherwise yields when any any number of them have been found

    Yields:
        JSON structures that matches :func:`all` or :func:`any` of given
        ``key_patterns``

    """
    check: Callable[[Iterable[bool]], bool] = all if all_ else any
    for json_struct in walk_structures(json_content):
        to_check: list[bool] = []
        for key_pattern in key_patterns:
            key_result = dict(query_keys(json_struct, key_pattern))
            to_check.append(bool(key_result))
        if check(to_check):
            yield json_struct


def edit(
    json_value: JsonValue,
    matcher: Callable[[JsonKey, JsonValue], bool],
    converter: Callable[[JsonKey, JsonValue], Iterator[tuple[JsonKey, JsonValue]]],
    drop: bool = True,
) -> None:
    R"""Add a new field for each key of the ``obs_keys`` found in the JSON using
    ``obs_new_mapping`` on the observed key and value to generate the new field
    key and value.

    This function alters ``json_value`` in situ.

    Args:
        json_value: JSON structured content
        matcher: Function that takes JSON key and value as arguments and
            returns ``True`` if this pair is a match, ``False`` otherwise
        converter: Function that takes JSON key and value as arguments and
            yields JSON key and value pairs to incorporate to JSON content
        drop: Flag indicating if matched key-value pair should be removed or not

    Returns:
        ``None``: JSON content is modified inplace

    """
    for json_struct in walk_structures(json_value):
        for key, val in list(json_struct.items()):
            if not matcher(key, val):
                continue
            if drop:
                del json_struct[key]
            for new_key, new_val in converter(key, val):
                json_struct[new_key] = new_val


@one_or_many
def apply_mapping(
    json_content: JsonContent,
    obs_new_mapping: Mapping[JsonKey, Callable[[JsonKey, JsonValue], JsonValue]],
) -> None:
    R"""Searches for keys in ``obs_new_mapping`` and replace their values with the
    results of calling ``obs_new_mapping`` value with observed key and value as
    arguments (in that order).

    This function alters ``json_content`` in situ.

    Args:
        json_content: JSON structured content
        obs_new_mapping: Dictionary that maps each key with the function that
            is used for the replacement.

    Returns:
        ``None``: JSON configuration is modified inplace.

    """
    for json_struct in walk_structures(json_content):
        for key, function in obs_new_mapping.items():
            if key in json_struct:
                obs_val = json_struct[key]
                json_struct[key] = function(key, obs_val)


@one_or_many
def convert_keys_to_naming_convention(
    json_content: JsonContent,
    from_nc: NamingConvention = 'snake_case',
    dest_nc: NamingConvention = 'lowerCamelCase',
) -> None:
    """Converts JSON with keys written in any supported :class:`NamingConvention`
    to any other supported :class:`NamingConvention`. Use ``lowerCamelCase`` for
    Energyworx API format.

    This function alters ``json_content`` in situ.

    Args:
        json_content: Content of the JSON file that has to be converted.
        from_nc: Current naming convention of the keys.
        dest_nc: Resulting naming convention of the keys.

    Returns:
        JSON content with keys converted.

    """

    def convert_keys(key: str, val: JsonValue) -> Iterator[tuple[JsonKey, JsonValue]]:
        yield convert_name_to_naming_convention(key, from_nc, dest_nc), val

    edit(json_content, matcher=lambda *_: True, converter=convert_keys)


def extract_typed_dict(json_content: JsonContent) -> JsonContent:
    # TODO Santi: Implement this method
    raise NotImplementedError('This method is not implemented yet')


