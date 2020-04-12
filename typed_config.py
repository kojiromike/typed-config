#!/usr/bin/env python

"""
Builds a configuration object out of type annotations.

Define a subclass with annotations:

>>> class BasicConfig(TypedConfig):
...     INTEGER: int
...     FLOAT: float
...     COMPLEX: complex
...     BOOLEAN: bool
...     STRING: str

Provide required values in the environment or other means supported by python-decouple:

>>> import os
>>> os.environ.update({"INTEGER": "6",
...                    "FLOAT": "5.6",
...                    "COMPLEX": "3+4j",
...                    "BOOLEAN": "true",
...                    "STRING": "abcdefg"})

Configuration is evaluated at instantiation time:

>>> c = BasicConfig()
>>> c.INTEGER, c.FLOAT, c.COMPLEX, c.BOOLEAN, c.STRING
(6, 5.6, (3+4j), True, 'abcdefg')

Values without defaults are required:

>>> class RequiredConfig(TypedConfig):
...     MUST_HAVE: str
>>> RequiredConfig()
Traceback (most recent call last):
    ...
decouple.UndefinedValueError: MUST_HAVE not found. Declare it as envvar or define a default value.

Values with optional types have a default value of None:

>>> class OptionalConfig(TypedConfig):
...     MAYBE: t.Optional[int]
>>> c = OptionalConfig()
>>> c.MAYBE is None
True

Values with literal assignments get that value by default:

>>> class DefaultConfig(TypedConfig):
...     DEFAULT: float = 5.8
>>> DefaultConfig().DEFAULT
5.8

But default values are still overridden by the environment or settings:

>>> os.environ["DEFAULT"] = "2"
>>> DefaultConfig().DEFAULT
2.0

Of course this applies to optional types as well:

>>> os.environ["MAYBE"] = "4"
>>> OptionalConfig().MAYBE
4

List annotations are automatically cast using decouple.Csv:

>>> os.environ["FLOATS"] = "2,3.6,7"
>>> class ListConfig(TypedConfig):
...     FLOATS: t.List[float]
>>> ListConfig().FLOATS
[2.0, 3.6, 7.0]

But can still be optional or have defaults:

>>> class DefaultListConfig(TypedConfig):
...     MAYBE_STRINGS: t.Optional[t.List[str]]
...     INTEGERS: t.List[int] = " 4, 100, 12"
>>> c = DefaultListConfig()
>>> c.MAYBE_STRINGS is None, c.INTEGERS
(True, [4, 100, 12])

You can provide additional casts for types:

>>> import pathlib as p, base64
>>> os.environ['BIN64'] = 'aGVsbG8gd29ybGQ='
>>> class PathConfig(TypedConfig):
...     SOMEWHERE: p.Path = '/tmp'
...     BIN64: bytes
>>> c = PathConfig({p.Path: p.Path, bytes: lambda s: base64.b64decode(str.encode(s))})
>>> c.SOMEWHERE.name, c.BIN64
('tmp', b'hello world')

Names starting with underscores are ignored.
Names can be explicitly ignored as well.
This is useful when you want to provide a literal or your own config manually.

>>> class IgnoredValueConfig(TypedConfig):
...     NORMAL_BYTES: bytes = 'hi'
...     APP_PATH = p.Path(__file__).parent.absolute()
...     _NOTHING: int
...     BIN64: bytes = decouple.config('BIN64', cast=lambda s: base64.b64decode(str.encode(s)))
>>> c = IgnoredValueConfig(ignored_names={'APP_PATH', 'BIN64'})
>>> c.APP_PATH.name
'typed-config'
>>> hasattr(c, '_NOTHING')
False

It's also the only way to cast one type two different ways.

>>> c.NORMAL_BYTES, c.BIN64
(b'hi', b'hello world')
"""

import functools, typing as t, decouple, distutils.util


##
# We need to map all supported type annotations into cast functions.
# A cast function is a function that takes a string and returns a particular type.
# Most primitive types in Python already do this: int('9') -> 9.
SomeType = t.TypeVar('SomeType')
CastType = t.Callable[[t.Optional[str]], t.Optional[SomeType]]


def optional(cast: t.Callable[[str], SomeType]) -> CastType:
    """A decorator that takes a cast function and returns an optional cast function."""
    @functools.wraps(cast)
    def maybe(s: t.Optional[str]) -> t.Optional[SomeType]:
        return cast(s) if s else None
    return maybe


cast_bool = decouple.Config(None)._cast_boolean

default_casts = {
    int: int,
    float: float,
    complex: complex,
    bool: cast_bool,
    str: str,
    bytes: str.encode,

    t.List[int]: decouple.Csv(int),
    t.List[float]: decouple.Csv(float),
    t.List[complex]: decouple.Csv(complex),
    t.List[bool]: decouple.Csv(cast_bool),
    t.List[str]: decouple.Csv(str),
    t.List[bytes]: decouple.Csv(str.encode),

    t.Optional[int]: optional(int),
    t.Optional[float]: optional(float),
    t.Optional[complex]: optional(complex),
    t.Optional[bool]: optional(cast_bool),
    t.Optional[str]: optional(str),
    t.Optional[bytes]: optional(str.encode),

    t.Optional[t.List[int]]: optional(decouple.Csv(int)),
    t.Optional[t.List[float]]: optional(decouple.Csv(float)),
    t.Optional[t.List[complex]]: optional(decouple.Csv(complex)),
    t.Optional[t.List[bool]]: optional(decouple.Csv(cast_bool)),
    t.Optional[t.List[str]]: optional(decouple.Csv(str)),
    t.Optional[t.List[bytes]]: optional(decouple.Csv(str.encode)),
}


def is_optional(type_: t.Type) -> bool:
    """Return True if the given type is t.Optional[SomeType]"""
    try:
        orig, args = type_.__origin__, type_.__args__
    except AttributeError:
        return False
    return ((orig == t.Union) and (len(args) == 2) and (type(None) in args))


class TypedConfig(object):
    """
    Build a configuration object out of the annotations of the subclass.
    """

    def __init__(self, casts: t.Optional[t.Mapping[SomeType, CastType]] = None, ignored_names: t.Container[str] = ()) -> None:
        """
        Supply or replace the attributes of the subclass with the configured values
        according to their type annotations and defaults.
        """
        casts = {**default_casts, **(casts or {})}
        for name, type_ in self.__annotations__.items():
            if name.startswith('_') or name in ignored_names:
                continue
            cfg = functools.partial(decouple.config, name, cast=casts[type_])
            if hasattr(self, name):  # Subclass has a default value
                attribute = getattr(self, name)
                setattr(self, name, cfg(default=attribute))
            elif is_optional(type_):  # default=None
                setattr(self, name, cfg(default=None))
            else:
                setattr(self, name, cfg())
