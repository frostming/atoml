import datetime as _datetime

from typing import IO, Tuple

from ._utils import parse_rfc3339
from .container import Container
from .items import (
    AoT,
    Array,
    Bool,
    Comment,
    Date,
    DateTime,
    Float,
    InlineTable,
    Integer,
)
from .items import Item as _Item
from .items import Key, String, Table, Time, Trivia, Whitespace, item
from .parser import Parser
from .toml_document import TOMLDocument as _TOMLDocument


def loads(string: str) -> _TOMLDocument:
    """
    Parses a string into a TOMLDocument.

    Alias for parse().
    """
    return parse(string)


def dumps(data: _TOMLDocument, sort_keys: bool = False) -> str:
    """
    Dumps a TOMLDocument into a string.
    """
    if not isinstance(data, _TOMLDocument) and isinstance(data, dict):
        data = item(data, _sort_keys=sort_keys)

    return data.as_string()


def load(fp: IO) -> _TOMLDocument:
    """
    Load toml document from a file-like object.
    """
    return parse(fp.read())


def dump(data: _TOMLDocument, fp: IO[str], *, sort_keys: bool = False) -> None:
    """
    Dump a TOMLDocument into a writable file stream.
    """
    fp.write(dumps(data, sort_keys=sort_keys))


def parse(string: str) -> _TOMLDocument:
    """
    Parses a string into a TOMLDocument.
    """
    return Parser(string).parse()


def document() -> _TOMLDocument:
    """
    Returns a new TOMLDocument instance.
    """
    return _TOMLDocument()


# Items
def integer(raw: str) -> Integer:
    return item(int(raw))


def float_(raw: str) -> Float:
    return item(float(raw))


def boolean(raw: str) -> Bool:
    return item(raw == "true")


def string(raw: str) -> String:
    return item(raw)


def date(raw: str) -> Date:
    value = parse_rfc3339(raw)
    if not isinstance(value, _datetime.date):
        raise ValueError("date() only accepts date strings.")

    return item(value)


def time(raw: str) -> Time:
    value = parse_rfc3339(raw)
    if not isinstance(value, _datetime.time):
        raise ValueError("time() only accepts time strings.")

    return item(value)


def datetime(raw: str) -> DateTime:
    value = parse_rfc3339(raw)
    if not isinstance(value, _datetime.datetime):
        raise ValueError("datetime() only accepts datetime strings.")

    return item(value)


def array(raw: str = None) -> Array:
    if raw is None:
        raw = "[]"

    return value(raw)


def table() -> Table:
    return Table(Container(), Trivia(), False)


def inline_table() -> InlineTable:
    return InlineTable(Container(), Trivia(), new=True)


def aot() -> AoT:
    return AoT([])


def key(k: str) -> Key:
    return Key(k)


def value(raw: str) -> _Item:
    return Parser(raw)._parse_value()


def key_value(src: str) -> Tuple[Key, _Item]:
    return Parser(src)._parse_key_value()


def ws(src: str) -> Whitespace:
    return Whitespace(src, fixed=True)


def nl() -> Whitespace:
    return ws("\n")


def comment(string: str) -> Comment:
    return Comment(Trivia(comment_ws="  ", comment="# " + string))
