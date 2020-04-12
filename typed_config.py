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
"""

import functools, typing as t, decouple

NoneType = type(None)
scalars = int, float, complex, bool, str, bytes, None
optional_scalars = tuple(t.Optional[s] for s in scalars)
lists = tuple(t.List[s] for s in scalars)
optional_lists = tuple(t.Optional[l] for l in lists)
optionals = optional_scalars + optional_lists


def _cast(type_):
    """
    Infer the decouple.config cast argument from the type annotation.

    Currently supported:
    - primitive scalar types,
    - lists of scalars,
    - optional scalars
    """
    if type_ == bytes:
        raise NotImplementedError
    if type_ in scalars:
        return type_
    if type_ in optionals:
        return _cast_optional(type_)
    if type_ in lists:
        return _cast_list(type_)
    raise NotImplementedError(f"No inference implementation exists for {type_}")


def _cast_optional(type_):
    """
    Infer the decouple.config cast argument from the inner type annotation of an optional type.
    """
    just = next(_cast(a) for a in type_.__args__ if a != NoneType)
    def cast(v):
        if v is None:
            return v
        if just == bool:
            return decouple.Config(None)._cast_boolean(val)
        return just(v)
    return cast


def _cast_list(type_):
    """
    Infer the decouple.config cast argument from the inner type annotation of a list type.
    """
    return decouple.Csv(type_.__args__[0])


class TypedConfig(object):
    """
    Build a configuration object out of the annotations of the subclass.
    """

    def __init__(self):
        """
        Supply or replace the attributes of the subclass with the configured values
        according to their type annotations and defaults.
        """
        for name, type_ in self.__annotations__.items():
            if name.startswith('_'):
                continue
            cfg = functools.partial(decouple.config, name, cast=_cast(type_))
            if hasattr(self, name):  # Subclass has a default value
                attribute = getattr(self, name)
                setattr(self, name, cfg(default=attribute))
            elif type_ in optionals:  # default=None
                setattr(self, name, cfg(default=None))
            else:
                setattr(self, name, cfg())
