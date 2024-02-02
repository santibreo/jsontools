"""Module containing functions that simplifies interactions with data structured
as JSON."""
from __future__ import annotations

import re
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from functools import wraps
from typing import Callable
from typing import Literal
from typing import TypeVar
from typing import Union


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
    R"""Traverses a nested JSON file returning every key-value pair found,
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


#  # This function dumps a rule to a Python file
#  def dump_rule_py(rule: dict, dirname: Path, filename: str | Path) -> None:
#      """Dumps a rule to a ``.py`` file from ``codeBlob`` field"""
#      dirname.mkdir(parents=True, exist_ok=True)
#      with open(dirname / filename, "w", encoding="latin-1") as file:
#          file.write(rule["codeBlob"])
#
#
#  # This function loads a rule from a Python file
#  def load_py(filename: str | Path) -> str:
#      """Loads a ``.py`` file as string"""
#      with open(filename, "r", encoding="latin-1") as file:
#          code_blob = file.read()
#      return code_blob
#
#
#  # %% RULES MANIPULATION FUNCTIONS
#  RULE_PARAMS_DEFAULTS = load_json(
#      _PACKAGE_DATA_PATH / "schemas/rule_param_templates.json"
#  )
#  RULE_API_DEFAULT_JSON = load_json(
#      _PACKAGE_DATA_PATH / "schemas/rule_template.json"
#  )
#
#
#  # This function extracts argument name, type and description from function docstring
#  def arg_name_type_and_desc_from_docstring(
#      args_docstring: str, regexp: str = r""
#  ) -> Generator[tuple[str, Union[str, None], str], None, None]:
#      """
#      Extracts each argument with its type from python docstring google formatted
#
#      Args:
#          args_docstring (str): Docstring that contains the arguments description.
#
#      Returns:
#          Generator[tuple[str, str]]: Tuples of argument-name and argument-type and
#              argument-description
#      """
#      pattern = re.compile(
#          regexp
#          or r"^\s+(?P<name>[*\\\w]+)\s?(?P<type>\([\w\[\]]+\))?:(?P<doc>.*)"
#      )
#      arg_name, arg_type, arg_doc = "", "", ""
#      for line in args_docstring.splitlines():
#          # Ignore empty lines
#          if line.replace(" ", "") == "":
#              # arg_name, arg_type, arg_doc = "", "", ""
#              continue
#          # Complete description when it is long
#          if (match := re.match(pattern, line)) is None:
#              arg_doc += f" {line.strip()}"
#              continue
#          # Yield previous argument
#          if arg_name != "":
#              yield arg_name, arg_type, arg_doc.strip()
#          # Populate new argument
#          arg_name, arg_type, arg_doc = map(match.group, ("name", "type", "doc"))
#          # Clean argument type if defined
#          if arg_type is not None:
#              arg_type = re.sub(r"(\(|\))", "", arg_type).strip()
#      # Yield last argument (if not yielded yet)
#      if arg_name != "":
#          yield arg_name, arg_type, arg_doc.strip()
#
#
#  # This function extracts name, type and default value from function signature
#  def arg_name_type_and_default_from_signature(
#      signature: str, skip_self: bool = True, skip_starred: bool = True
#  ) -> Generator[tuple[str, Union[str, None], Union[str, None]], None, None]:
#      """
#      Extracts each argument name with its type and default value from function
#      signature. Default is returned as string, if no default None is returned
#      instead. If no type is provided for the argument, None is also returned.
#
#      Args:
#          signature (str): Function signature.
#          skip_self (bool): Determines if 'self' and 'cls' arguments should be
#              skipped when analysing class methods.
#          skip_starred (bool): Determines if arguments begining with a star ('*')
#              should be skipped.
#      Returns:
#          Generator[tuple[str, str | None, str | None]]: Tuples of argument-name,
#              argument-type and argument-default. All as strings except when type
#              or default are not defined (when not define they are None).
#      """
#      for arg in re.split(r"\s?,\s?", signature):
#          rest, *arg_default = arg.split("=")
#          arg_name, *arg_type = rest.split(":")
#          if skip_self and any(x in arg_name for x in ("self", "cls")):
#              continue
#          if skip_starred and arg_name.strip().startswith("*"):
#              continue
#          yield (
#              arg_name.strip(),
#              arg_type[0].strip() if arg_type else None,
#              re.sub(r"(\"|')", "", arg_default[0].strip())
#              if arg_default
#              else None,
#          )
#
#
#  # THis function extracts arguments information from function docstring
#  def process_args_from_function_docstring(
#      func_doc: str, func_sig: str
#  ) -> Generator[tuple[str, dict[str, str]], None, None]:
#      """
#      Extracts arguments name, type, default value and description from function
#      docstring google formatted (arguments are described between 'Args:' and
#      'Returns:' lines) and function signature.
#
#      Args:
#          func_doc: Function docstring.
#          func_sig: Function signature.
#
#      Returns:
#           2-Tuples of argument type and dictionary with argument attributes
#           required by Energyworx API.
#      """
#      try:
#          func_params_doc = func_doc.split("Args:")[1].split("Returns:")[0]
#      except AttributeError:
#          raise ValueError(f"Cannot extract arguments information from docstring")
#      # Dictionary [arg_name, tuple[arg_type, arg_desc]]
#      args_from_doc = dict(
#          (
#              (x, y)
#              for x, *y in arg_name_type_and_desc_from_docstring(func_params_doc)
#          )
#      )
#      # Create parameters dictionaries (signature has higher priority)
#      args_from_sig = arg_name_type_and_default_from_signature(func_sig)
#      for arg_name, arg_type, arg_default in args_from_sig:
#          # If arg_type is not defined in signature take it from docstring
#          if arg_type is None:
#              arg_type = args_from_doc[arg_name][0]
#          # Argument type must be defined
#          if arg_type is None:
#              raise AttributeError(f"{arg_name!r} has not type defined")
#          arg_dict = {
#              "name": arg_name,
#              "displayName": convert_name_to_naming_convention(
#                  arg_name, "snake_case", "Standard Display Name"
#              ),
#              "description": args_from_doc[arg_name][1],
#          }
#          # Add default value (as string) if defined
#          if arg_default is not None:
#              arg_dict["defaultValue"] = arg_default
#          yield arg_type, arg_dict
#
#
#  # This function processes Rule apply method
#  def process_apply_function_abstract_node(
#      func_asn: ast.FunctionDef,
#  ) -> dict[str, Any]:
#      """
#      Extracts description and every parameter config from apply function abstract
#      node.
#
#      Args:
#          func_an (ast.FunctionDef): ``apply`` method of the rule class abstract
#              node
#      Returns:
#          dict[str, Any]: Dictionary with the description found in apply docstring
#              and the params config as Energyworx API rule fields
#      """
#      func_info = dict()
#      func_doc, func_sig = ast.get_docstring(func_asn), ast.unparse(func_asn.args)
#      try:
#          func_desc, _ = func_doc.split("Args:")
#      except (ValueError, AttributeError):
#          raise RulePythonFileError(
#              "To upload rule, apply method must be well documented"
#          )
#      func_info["description"] = "".join(func_desc.splitlines())
#      func_info["params"] = []
#      for arg_type, arg_dict in process_args_from_function_docstring(
#          func_doc, func_sig
#      ):
#          # Take schema for this arg_type from rule_params_template
#          try:
#              arg_default_dict = deepcopy(RULE_PARAMS_DEFAULTS[arg_type])
#          except KeyError:
#              arg_default_dict = deepcopy(RULE_PARAMS_DEFAULTS["str"])
#              print(
#                  f"Cannot convert type {arg_type} to platform types. Using text."
#              )
#          arg_default_dict.update(arg_dict)
#          func_info["params"].append(arg_default_dict)
#      return func_info
#
#
#  # This function loads rule .py file into EWX API rule config
#  def load_rule_py(rule_pyfilepath: Path, filename_prefix: str = "") -> dict:
#      """
#      Converts rule ``.py`` file into a rule configuration that can be posted to
#      Energyworx API. Also renames ``.py`` file to standard rule name convention.
#
#      Args:
#          rule_pyfilepath (Path): Path to rule Python file.
#
#      Returns:
#          dict[str, Any]: Dictionary being the schema defined by Energyworx API.
#      """
#      # Abstract Syntax Tree for reliable python code parsing
#      rule_dict = deepcopy(RULE_API_DEFAULT_JSON)
#      if not rule_pyfilepath.exists() or not rule_pyfilepath.suffix == ".py":
#          raise RulePythonFileError(
#              f"{rule_pyfilepath} is not a valid Python file"
#          )
#      rule_dict["ruleType"] = rule_pyfilepath.parent.name
#      if rule_dict["ruleType"] not in RULE_TYPES:
#          print(f"Unknown rule type: {rule_dict['ruleType']!r}. Define it later.")
#          # raise RulePythonFileError(f"Unknown rule type: {rule_dict['ruleType']!r}")
#      # Module Abstract Syntax Tree
#      module_filename: str = rule_pyfilepath.name
#      module_root = ast.parse(
#          rule_pyfilepath.open().read(), module_filename, type_comments=True
#      )
#      # Code blob is whole source code
#      rule_dict["codeBlob"] = rule_pyfilepath.read_text()
#      # This way code lose format: rule_dict['codeBlob'] = ast.unparse(module_root)
#      # Rule class is the only class that inherits from AbstractRule
#      rule_parents = ("AbstractRule", "TransformRule")
#      class_node = next(
#          (
#              n
#              for n in ast.iter_child_nodes(module_root)
#              if isinstance(n, ast.ClassDef)
#              and getattr(n, "bases", [])
#              and n.bases[0].id in rule_parents
#          ),
#          None,
#      )
#      if class_node is None:
#          raise RulePythonFileError(
#              f"Cannot find a class that inherits from {','.join(rule_parents)}"
#          )
#      # Only rule names are obtained from class node
#      rule_dict["name"] = convert_name_to_naming_convention(
#          class_node.name, "CamelCase", "snake_case"
#      )
#      rule_dict["displayName"] = convert_name_to_naming_convention(
#          rule_dict["name"], "snake_case", "Standard Display Name"
#      )
#      # Rename rule file if necessary
#      rule_good_stem: str = rule_dict["displayName"].replace(" ", "_").lower()
#      if not rule_good_stem.startswith(filename_prefix):
#          rule_good_stem = filename_prefix + rule_good_stem
#      if not rule_good_stem.endswith(rule_dict["ruleType"]):
#          rule_good_stem = rule_good_stem + "_" + rule_dict["ruleType"]
#      if rule_good_stem != rule_pyfilepath.stem:
#          new_rule_pyfilepath = rule_pyfilepath.rename(
#              rule_pyfilepath.with_stem(rule_stem)
#          )
#          print(f"{rule_pyfilepath} renamed to: {new_rule_pyfilepath}")
#      # Process rule parameters
#      apply_node = next(
#          (
#              n
#              for n in ast.iter_child_nodes(class_node)
#              if isinstance(n, ast.FunctionDef) and n.name == "apply"
#          ),
#          None,
#      )
#      if apply_node is None:
#          raise RulePythonFileError(
#              "Your rule does not contain an apply method"
#          )
#      rule_dict.update(process_apply_function_abstract_node(apply_node))
#      return rule_dict
#
#
#  # This function dumps EWX API rule config into .py file.
#  def dump_rule_py(
#      rule_config: dict[str, Any],
#      dirpath_raw: Optional[PathLike] = None,
#      *,
#      ruletype_in_name: bool = False,
#      filename_prefix: str = "",
#  ) -> JsonConfig:
#      """
#      Converts rule configuration into a rule ``.py`` giving it a name acording
#      to standard rule name convention.
#
#      Args:
#          rule_config: Rule configuration as it comes from Energyworx API.
#          dirpath_raw: Optional directory path to host rule python file. If not
#              given python file is not written.
#          ruletype_in_name: Flag indicating if the rule type must be incorporated
#              to rule name, class name and python filename as a suffix.
#          filename_prefix: Prefix to incorporate to rule python filename.
#
#      Returns:
#          Rule configuration (with correct naming) that can be uploaded to
#          Energyworx API
#      """
#      if isinstance(rule_config, list):
#          raise ResourceJsonError(
#              f"Configuration schema is not a valid rule"
#          )
#      # Module Abstract Syntax Tree
#      module_root = ast.parse(
#          rule_config["codeBlob"], "rule_config", type_comments=True
#      )
#      # Rule class is the only class that inherits from AbstractRule OR TransformRule
#      rule_parents = ("AbstractRule", "TransformRule")
#      class_node = next(
#          (
#              n
#              for n in ast.iter_child_nodes(module_root)
#              if isinstance(n, ast.ClassDef)
#              and getattr(n, "bases", [])
#              and n.bases[0].id in rule_parents
#          ),
#          None,
#      )
#      if class_node is None:
#          raise RulePythonFileError(
#              f"Cannot find a class that inherits from: {', '.join(rule_parents)}"
#          )
#      # Fix rule name
#      if ruletype_in_name and not class_node.name.lower().endswith(
#          rule_config["ruleType"].lower()
#      ):
#          class_node.name += rule_config["ruleType"].capitalize()
#          rule_config["codeBlob"] = ast.unparse(module_root)
#      rule_config["name"] = convert_name_to_naming_convention(
#          class_node.name, "CamelCase", "snake_case"
#      )
#      rule_config["displayName"] = convert_name_to_naming_convention(
#          class_node.name, "CamelCase", "Standard Display Name"
#      )
#      rule_pyfilename = f"{filename_prefix}_{rule_config['name']}.py"
#
#      # Write python file
#      if dirpath_raw is not None:
#          dirpath: Path = Path(dirpath_raw)
#          if not dirpath.is_dir():
#              raise RulePythonFileError(f"{dirpath} is not a directory.")
#          if dirpath.name != rule_config["ruleType"]:
#              dirpath = dirpath / rule_config["ruleType"]
#          rule_pyfilepath: Path = dirpath / rule_pyfilename
#          rule_pyfilepath.parent.mkdir(exist_ok=True, parents=True)
#          with rule_pyfilepath.open("w", encoding="latin-1") as _file:
#              _file.write(rule_config["codeBlob"])
#      return rule_config
#
#
#  if __name__ == "__main__":
#      import doctest
#
#      doctest.testmod()
