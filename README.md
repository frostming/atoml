**UNMAINTAINED: _This project has been merged back to [tomlkit] and is no longer maintained. Please switch to `tomlkit>=0.8.0`._**

[pypi_version]: https://img.shields.io/pypi/v/atoml.svg?logo=python&logoColor=white
[python_versions]: https://img.shields.io/pypi/pyversions/atoml.svg?logo=python&logoColor=white
[github_license]: https://img.shields.io/github/license/frostming/atoml.svg?logo=github&logoColor=white
[tomlkit]: https://github.com/sdispater/tomlkit

[![PyPI Version][pypi_version]](https://pypi.python.org/pypi/atoml/)
[![Python Versions][python_versions]](https://pypi.python.org/pypi/atoml/)
[![License][github_license]](https://github.com/frostming/atoml/blob/master/LICENSE)
![Github Actions](https://github.com/frostming/atoml/workflows/Continuous%20Integration/badge.svg)
[![codecov](https://codecov.io/gh/frostming/atoml/branch/main/graph/badge.svg?token=erZTquL5n0)](https://codecov.io/gh/frostming/atoml)

# ATOML - Yet another style-preserving TOML library for Python

ATOML is a **1.0.0rc1-compliant** [TOML](https://github.com/toml-lang/toml) library.

It includes a parser that preserves all comments, indentations, whitespace and internal element ordering, and makes them accessible and editable via an intuitive API.

You can also create new TOML documents from scratch using the provided helpers.

The name comes from the famous Japanese cartoon character **鉄腕アトム(Atom)**.

_**Implementation Change**: Start from 1.0, ATOML is a fork of [tomlkit v0.7.0][tomlkit] with less bugs and inconsistency._

## Usage

### Parsing

ATOML comes with a fast and style-preserving parser to help you access
the content of TOML files and strings.

```python
>>> from atoml import dumps
>>> from atoml import parse  # you can also use loads

>>> content = """[table]
... foo = "bar"  # String
... """
>>> doc = parse(content)

# doc is a TOMLDocument instance that holds all the information
# about the TOML string.
# It behaves like a standard dictionary.

>>> assert doc["table"]["foo"] == "bar"

# The string generated from the document is exactly the same
# as the original string
>>> assert dumps(doc) == content
```

### Modifying

ATOML provides an intuitive API to modify TOML documents.

```python
>>> from atoml import dumps
>>> from atoml import parse
>>> from atoml import table

>>> doc = parse("""[table]
... foo = "bar"  # String
... """)

>>> doc["table"]["baz"] = 13

>>> dumps(doc)
"""[table]
foo = "bar"  # String
baz = 13
"""

# Add a new table
>>> tab = table()
>>> tab.add("array", [1, 2, 3])

>>> doc["table2"] = tab

>>> dumps(doc)
"""[table]
foo = "bar"  # String
baz = 13

[table2]
array = [1, 2, 3]
"""

# Remove the newly added table
>>> doc.remove("table2")
# del doc["table2] is also possible
```

### Writing

You can also write a new TOML document from scratch.

Let's say we want to create this following document:

```toml
# This is a TOML document.

title = "TOML Example"

[owner]
name = "Tom Preston-Werner"
organization = "GitHub"
bio = "GitHub Cofounder & CEO\nLikes tater tots and beer."
dob = 1979-05-27T07:32:00Z # First class dates? Why not?

[database]
server = "192.168.1.1"
ports = [ 8001, 8001, 8002 ]
connection_max = 5000
enabled = true
```

It can be created with the following code:

```python
>>> from atoml import comment
>>> from atoml import document
>>> from atoml import nl
>>> from atoml import table

>>> doc = document()
>>> doc.add(comment("This is a TOML document."))
>>> doc.add(nl())
>>> doc.add("title", "TOML Example")
# Using doc["title"] = "TOML Example" is also possible

>>> owner = table()
>>> owner.add("name", "Tom Preston-Werner")
>>> owner.add("organization", "GitHub")
>>> owner.add("bio", "GitHub Cofounder & CEO\nLikes tater tots and beer.")
>>> owner.add("dob", datetime(1979, 5, 27, 7, 32, tzinfo=utc))
>>> owner["dob"].comment("First class dates? Why not?")

# Adding the table to the document
>>> doc.add("owner", owner)

>>> database = table()
>>> database["server"] = "192.168.1.1"
>>> database["ports"] = [8001, 8001, 8002]
>>> database["connection_max"] = 5000
>>> database["enabled"] = True

>>> doc["database"] = database
```

## Installation

If you are using [PDM](https://pdm.fming.dev),
add `atoml` to your `pyproject.toml` file by using:

```bash
pdm add atoml
```

If not, you can use `pip`:

```bash
pip install atoml
```

## Migrate from TOMLKit

ATOML comes with full compatible API with TOMLKit, you can easily do a Replace All of `tomlkit` to `atoml` or:

```python
import atoml as tomlkit
```

ATOML differs from TOMLkit in the following ways:

- Python 3.6+ support only
- Tables and arrays are subclasses of `MutableMapping` and `MutableSequence` respectively, to reduce some inconsistency between the container behaviors
- `load` and `dump` methods added
- [Less bugs](https://github.com/frostming/atoml/issues/9)
