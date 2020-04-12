# typed-config 

![Doctests Status Badge](https://github.com/kojiromike/typed-config/workflows/doctests/badge.svg)
![Mypy Status Badge](https://github.com/kojiromike/typed-config/workflows/mypy/badge.svg)

## Automatically build Python configuration structures from type annotations

Define a subclass with annotations:

```python
>>> from typed_config import TypedConfig
>>> class BasicConfig(TypedConfig):
...     INTEGER: int
...     FLOAT: float
...     COMPLEX: complex
...     BOOLEAN: bool
...     STRING: str
>>>
```

Provide required values in the environment or other means supported by python-decouple:

```python
>>> import os
>>> os.environ.update({"INTEGER": "6",
...                    "FLOAT": "5.6",
...                    "COMPLEX": "3+4j",
...                    "BOOLEAN": "true",
...                    "STRING": "abcdefg"})
>>>
```

Configuration is evaluated at instantiation time:

```python
>>> c = BasicConfig()
>>> c.INTEGER, c.FLOAT, c.COMPLEX, c.BOOLEAN, c.STRING
(6, 5.6, (3+4j), True, 'abcdefg')
>>>
```

Values without defaults are required:

```python
>>> class RequiredConfig(TypedConfig):
...     MUST_HAVE: str
>>> RequiredConfig()
Traceback (most recent call last):
    ...
decouple.UndefinedValueError: MUST_HAVE not found. Declare it as envvar or define a default value.
>>>
```

Values with optional types have a default value of None:

```python
>>> import typing as t
>>> class OptionalConfig(TypedConfig):
...     MAYBE: t.Optional[int]
>>> c = OptionalConfig()
>>> c.MAYBE is None
True
>>>
```

Values with literal assignments get that value by default:

```python
>>> class DefaultConfig(TypedConfig):
...     DEFAULT: float = 5.8
>>> DefaultConfig().DEFAULT
5.8
>>>
```

But default values are still overridden by the environment or settings:

```python
>>> os.environ["DEFAULT"] = "2"
>>> DefaultConfig().DEFAULT
2.0
>>>
```

Of course this applies to optional types as well:

```python
>>> os.environ["MAYBE"] = "4"
>>> OptionalConfig().MAYBE
4
>>>
```

List annotations are automatically cast using decouple.Csv:

```python
>>> os.environ["FLOATS"] = "2,3.6,7"
>>> class ListConfig(TypedConfig):
...     FLOATS: t.List[float]
>>> ListConfig().FLOATS
[2.0, 3.6, 7.0]
>>>
```

But can still be optional or have defaults:

```python
>>> class DefaultListConfig(TypedConfig):
...     MAYBE_STRINGS: t.Optional[t.List[str]]
...     INTEGERS: t.List[int] = " 4, 100, 12"
>>> c = DefaultListConfig()
>>> c.MAYBE_STRINGS is None, c.INTEGERS
(True, [4, 100, 12])
>>>
"""
```

You can provide additional casts for types:

```python
>>> import pathlib as p, base64
>>> os.environ['BIN64'] = 'aGVsbG8gd29ybGQ='
>>> class PathConfig(TypedConfig):
...     SOMEWHERE: p.Path = '/tmp'
...     BIN64: bytes
>>> c = PathConfig({p.Path: p.Path, bytes: lambda s: base64.b64decode(str.encode(s))})
>>> c.SOMEWHERE.name, c.BIN64
('tmp', b'hello world')
>>>
```

Names starting with underscores are ignored.
Names can be explicitly ignored as well.
This is useful when you want to provide a literal or your own config manually.

```python
>>> class IgnoredValueConfig(TypedConfig):
...     _NOTHING: int
>>> c = IgnoredValueConfig()
>>> hasattr(c, '_NOTHING')
False
>>>
```

It's also the only way to cast one type two different ways.

```python
>>> import decouple
>>> class IgnoredValueConfig(TypedConfig):
...     NORMAL_BYTES: bytes = 'hi'
...     BIN64: bytes = decouple.config('BIN64', cast=lambda s: base64.b64decode(str.encode(s)))
>>> c = IgnoredValueConfig(ignored_names={'BIN64'})
>>> c.NORMAL_BYTES, c.BIN64
(b'hi', b'hello world')
>>>
```
