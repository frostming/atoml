AToml
=====

.. image:: https://img.shields.io/pypi/v/nine.svg
    :target: http://pypi.python.org/pypi/atoml
.. image:: https://travis-ci.org/frostming/atoml.svg?branch=master
    :target: https://travis-ci.org/frostming/atoml

This library is a Python implementation of `TOML <https://github.com/toml-lang/toml>`_ and conforms `v0.4.0 specs <https://github.com/toml-lang/toml/blob/master/versions/en/toml-v0.4.0.md>`_. This library runs on Python 2.7 and 3.5+.

The name comes from the famous Japanese cartoon character **鉄腕アトム(Atom)**

----

Installation
````````````

::

    $ pip install atoml

Usage
`````
The interface is the same as Python's built-in ``json`` library:

1. Use ``loads`` to read from a string object, ``load`` to read from a file object
2. Use ``dumps`` to convert a string object to TOML string, ``dump`` to write into a file passed as second argument.

License
```````
BSD2 License


Run Tests
`````````
This library passes all the tests in `toml-test <github.com/burntSushi/toml-test>`_, to run it, update the submodule first::

    $ git submodule init
    $ git submodule update

Then, install ``pytest`` and run ``pytest`` in project root.
