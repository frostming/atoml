import io
import json
import os

from datetime import date, datetime, time
from types import MappingProxyType

import pytest

import atoml

from atoml import dump, dumps, load, loads, parse
from atoml.exceptions import (
    InvalidCharInStringError,
    InvalidControlChar,
    InvalidDateError,
    InvalidDateTimeError,
    InvalidNumberError,
    InvalidTimeError,
    UnexpectedCharError,
)
from atoml.items import (
    AoT,
    Array,
    Bool,
    Date,
    DateTime,
    Float,
    InlineTable,
    Integer,
    Key,
    Table,
    Time,
)
from atoml.toml_document import TOMLDocument


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()

    raise TypeError(f"Type {type(obj)} not serializable")


@pytest.mark.parametrize(
    "example_name",
    [
        "example",
        "fruit",
        "hard",
        "sections_with_same_start",
        "pyproject",
        "0.5.0",
        "test",
        "newline_in_strings",
        "preserve_quotes_in_string",
        "string_slash_whitespace_newline",
        "table_names",
    ],
)
def test_parse_can_parse_valid_toml_files(example, example_name):
    assert isinstance(parse(example(example_name)), TOMLDocument)
    assert isinstance(loads(example(example_name)), TOMLDocument)


@pytest.mark.parametrize(
    "example_name",
    [
        "example",
        "fruit",
        "hard",
        "sections_with_same_start",
        "pyproject",
        "0.5.0",
        "test",
        "newline_in_strings",
        "preserve_quotes_in_string",
        "string_slash_whitespace_newline",
        "table_names",
    ],
)
def test_load_from_file_object(example_name):
    with open(
        os.path.join(os.path.dirname(__file__), "examples", example_name + ".toml"),
        encoding="utf-8",
    ) as fp:
        assert isinstance(load(fp), TOMLDocument)


@pytest.mark.parametrize("example_name", ["0.5.0", "pyproject", "table_names"])
def test_parsed_document_are_properly_json_representable(
    example, json_example, example_name
):
    doc = json.loads(json.dumps(parse(example(example_name)), default=json_serial))
    json_doc = json.loads(json_example(example_name))

    assert doc == json_doc


@pytest.mark.parametrize(
    "example_name,error",
    [
        ("section_with_trailing_characters", UnexpectedCharError),
        ("key_value_with_trailing_chars", UnexpectedCharError),
        ("array_with_invalid_chars", UnexpectedCharError),
        ("invalid_number", InvalidNumberError),
        ("invalid_date", InvalidDateError),
        ("invalid_time", InvalidTimeError),
        ("invalid_datetime", InvalidDateTimeError),
        ("trailing_comma", UnexpectedCharError),
        ("newline_in_singleline_string", InvalidControlChar),
        ("string_slash_whitespace_char", InvalidCharInStringError),
        ("array_no_comma", UnexpectedCharError),
        ("array_duplicate_comma", UnexpectedCharError),
        ("array_leading_comma", UnexpectedCharError),
        ("inline_table_no_comma", UnexpectedCharError),
        ("inline_table_duplicate_comma", UnexpectedCharError),
        ("inline_table_leading_comma", UnexpectedCharError),
        ("inline_table_trailing_comma", UnexpectedCharError),
    ],
)
def test_parse_raises_errors_for_invalid_toml_files(
    invalid_example, error, example_name
):
    with pytest.raises(error):
        parse(invalid_example(example_name))


@pytest.mark.parametrize(
    "example_name",
    [
        "example",
        "fruit",
        "hard",
        "sections_with_same_start",
        "pyproject",
        "0.5.0",
        "test",
        "table_names",
    ],
)
def test_original_string_and_dumped_string_are_equal(example, example_name):
    content = example(example_name)
    parsed = parse(content)

    assert content == dumps(parsed)


def test_a_raw_dict_can_be_dumped():
    s = dumps({"foo": "bar"})

    assert s == 'foo = "bar"\n'


def test_mapping_types_can_be_dumped():
    x = MappingProxyType({"foo": "bar"})
    assert dumps(x) == 'foo = "bar"\n'


def test_dumps_weird_object():
    with pytest.raises(TypeError):
        dumps(object())


def test_dump_to_file_object():
    doc = {"foo": "bar"}
    fp = io.StringIO()
    dump(doc, fp)
    assert fp.getvalue() == 'foo = "bar"\n'


def test_integer():
    i = atoml.integer("34")

    assert isinstance(i, Integer)


def test_float():
    i = atoml.float_("34.56")

    assert isinstance(i, Float)


def test_boolean():
    i = atoml.boolean("true")

    assert isinstance(i, Bool)


def test_date():
    dt = atoml.date("1979-05-13")

    assert isinstance(dt, Date)

    with pytest.raises(ValueError):
        atoml.date("12:34:56")


def test_time():
    dt = atoml.time("12:34:56")

    assert isinstance(dt, Time)

    with pytest.raises(ValueError):
        atoml.time("1979-05-13")


def test_datetime():
    dt = atoml.datetime("1979-05-13T12:34:56")

    assert isinstance(dt, DateTime)

    with pytest.raises(ValueError):
        atoml.time("1979-05-13")


def test_array():
    a = atoml.array()

    assert isinstance(a, Array)

    a = atoml.array("[1,2, 3]")

    assert isinstance(a, Array)


def test_table():
    t = atoml.table()

    assert isinstance(t, Table)


def test_inline_table():
    t = atoml.inline_table()

    assert isinstance(t, InlineTable)


def test_aot():
    t = atoml.aot()

    assert isinstance(t, AoT)


def test_key():
    k = atoml.key("foo")

    assert isinstance(k, Key)


def test_key_value():
    k, i = atoml.key_value("foo = 12")

    assert isinstance(k, Key)
    assert isinstance(i, Integer)


def test_string():
    s = atoml.string('foo "')

    assert s.value == 'foo "'
    assert s.as_string() == '"foo \\""'


def test_item_dict_to_table():
    t = atoml.item({"foo": {"bar": "baz"}})

    assert t.value == {"foo": {"bar": "baz"}}
    assert (
        t.as_string()
        == """[foo]
bar = "baz"
"""
    )


def test_item_mixed_aray():
    example = [{"a": 3}, "b", 42]
    expected = '[{a = 3}, "b", 42]'
    t = atoml.item(example)
    assert t.as_string().strip() == expected
    assert dumps({"x": {"y": example}}).strip() == "[x]\ny = " + expected
