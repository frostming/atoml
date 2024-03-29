import re
import string

from typing import Any, Iterator, List, Optional, Tuple, Type, Union

from ._compat import decode
from ._utils import RFC_3339_LOOSE, _escaped, parse_rfc3339
from .container import Container
from .exceptions import (
    EmptyTableNameError,
    InternalParserError,
    InvalidCharInStringError,
    InvalidControlChar,
    InvalidDateError,
    InvalidDateTimeError,
    InvalidNumberError,
    InvalidTimeError,
    InvalidUnicodeValueError,
    ParseError,
    UnexpectedCharError,
    UnexpectedEofError,
)
from .items import (
    AoT,
    Array,
    Bool,
    BoolType,
    Comment,
    Date,
    DateTime,
    Float,
    InlineTable,
    Integer,
    Item,
    Key,
    KeyType,
    Null,
    String,
    StringType,
    Table,
    Time,
    Trivia,
    Whitespace,
)
from .source import Source
from .toml_char import TOMLChar
from .toml_document import TOMLDocument


CTRL_I = 0x09  # Tab
CTRL_J = 0x0A  # Line feed
CTRL_M = 0x0D  # Carriage return
CTRL_CHAR_LIMIT = 0x1F
CHR_DEL = 0x7F


class Parser:
    """
    Parser for TOML documents.
    """

    def __init__(self, string: str) -> None:
        # Input to parse
        self._src = Source(decode(string))

        self._aot_stack = []

    @property
    def _state(self):
        return self._src.state

    @property
    def _idx(self):
        return self._src.idx

    @property
    def _current(self):
        return self._src.current

    @property
    def _marker(self):
        return self._src.marker

    def extract(self) -> str:
        """
        Extracts the value between marker and index
        """
        return self._src.extract()

    def inc(self, exception: Optional[Type[ParseError]] = None) -> bool:
        """
        Increments the parser if the end of the input has not been reached.
        Returns whether or not it was able to advance.
        """
        return self._src.inc(exception=exception)

    def inc_n(self, n: int, exception: Optional[ParseError] = None) -> bool:
        """
        Increments the parser by n characters
        if the end of the input has not been reached.
        """
        return self._src.inc_n(n=n, exception=exception)

    def consume(self, chars, min=0, max=-1):
        """
        Consume chars until min/max is satisfied is valid.
        """
        return self._src.consume(chars=chars, min=min, max=max)

    def end(self) -> bool:
        """
        Returns True if the parser has reached the end of the input.
        """
        return self._src.end()

    def mark(self) -> None:
        """
        Sets the marker to the index's current position
        """
        self._src.mark()

    def parse_error(self, exception=ParseError, *args):
        """
        Creates a generic "parse error" at the current position.
        """
        return self._src.parse_error(exception, *args)

    def parse(self) -> TOMLDocument:
        body = TOMLDocument(True)

        # Take all keyvals outside of tables/AoT's.
        while not self.end():
            # Break out if a table is found
            if self._current == "[":
                break

            # Otherwise, take and append one KV
            item = self._parse_item()
            if not item:
                break

            key, value = item
            if key is not None and key.is_dotted():
                # We actually have a table
                self._handle_dotted_key(body, key, value)
            elif not self._merge_ws(value, body):
                body.append(key, value)

            self.mark()

        while not self.end():
            key, value = self._parse_table()
            if isinstance(value, Table) and value.is_aot_element():
                # This is just the first table in an AoT. Parse the rest of the array
                # along with it.
                value = self._parse_aot(value, key.key)

            body.append(key, value)

        body.parsing(False)

        return body

    def _merge_ws(self, item: Item, container: Container) -> bool:
        """
        Merges the given Item with the last one currently in the given Container if
        both are whitespace items.

        Returns True if the items were merged.
        """
        last = container.last_item()
        if not last:
            return False

        if not isinstance(item, Whitespace) or not isinstance(last, Whitespace):
            return False

        start = self._idx - (len(last.s) + len(item.s))
        container.body[-1] = (
            container.body[-1][0],
            Whitespace(self._src[start : self._idx]),
        )

        return True

    def _is_child(self, parent: str, child: str) -> bool:
        """
        Returns whether a key is strictly a child of another key.
        AoT siblings are not considered children of one another.
        """
        parent_parts = tuple(self._split_table_name(parent))
        child_parts = tuple(self._split_table_name(child))

        if parent_parts == child_parts:
            return False

        return parent_parts == child_parts[: len(parent_parts)]

    def _split_table_name(self, name: str) -> Iterator[Key]:
        in_name = False
        current = ""
        original = ""
        t = KeyType.Bare
        parts = 0
        for c in name:
            c = TOMLChar(c)

            if c == ".":
                if in_name:
                    current += c
                    original += c
                    continue

                if not current:
                    raise self.parse_error()

                yield Key(current.strip(), t=t, sep="", original=original)

                parts += 1

                current = original = ""
                t = KeyType.Bare
            elif c in {"'", '"'}:
                if in_name:
                    if c == t.value:
                        in_name = False
                    else:
                        current += c
                else:
                    if (
                        current.strip()
                        and TOMLChar(current[-1]).is_spaces()
                        and not parts
                    ):
                        raise self.parse_error()

                    in_name = True
                    t = KeyType.Literal if c == "'" else KeyType.Basic
                original += c
            elif in_name or c.is_bare_key_char():
                current += c
                original += c
            elif c.is_spaces():
                # A space is only valid at this point
                # if it's in between parts.
                # We store it for now and will check
                # later if it's valid
                current += c
                original += c
            else:
                raise self.parse_error()

        if current.strip():
            yield Key(current.strip(), t=t, sep="", original=original)

    def _parse_item(self) -> Optional[Tuple[Optional[Key], Item]]:
        """
        Attempts to parse the next item and returns it, along with its key
        if the item is value-like.
        """
        self.mark()
        with self._state as state:
            while True:
                c = self._current
                if c == "\n":
                    # Found a newline; Return all whitespace found up to this point.
                    self.inc()

                    return None, Whitespace(self.extract())
                elif c in " \t\r":
                    # Skip whitespace.
                    if not self.inc():
                        return None, Whitespace(self.extract())
                elif c == "#":
                    # Found a comment, parse it
                    indent = self.extract()
                    cws, comment, trail = self._parse_comment_trail()

                    return None, Comment(Trivia(indent, cws, comment, trail))
                elif c == "[":
                    # Found a table, delegate to the calling function.
                    return
                else:
                    # Begining of a KV pair.
                    # Return to beginning of whitespace so it gets included
                    # as indentation for the KV about to be parsed.
                    state.restore = True
                    break

        return self._parse_key_value(True)

    def _parse_comment_trail(self, parse_trail: bool = True) -> Tuple[str, str, str]:
        """
        Returns (comment_ws, comment, trail)
        If there is no comment, comment_ws and comment will
        simply be empty.
        """
        if self.end():
            return "", "", ""

        comment = ""
        comment_ws = ""
        self.mark()

        while True:
            c = self._current

            if c == "\n":
                break
            elif c == "#":
                comment_ws = self.extract()

                self.mark()
                self.inc()  # Skip #

                # The comment itself
                while not self.end() and not self._current.is_nl():
                    code = ord(self._current)
                    if code == CHR_DEL or code <= CTRL_CHAR_LIMIT and code != CTRL_I:
                        raise self.parse_error(InvalidControlChar, code, "comments")

                    if not self.inc():
                        break

                comment = self.extract()
                self.mark()

                break
            elif c in " \t\r":
                self.inc()
            else:
                raise self.parse_error(UnexpectedCharError, c)

            if self.end():
                break

        trail = ""
        if parse_trail:
            while self._current.is_spaces() and self.inc():
                pass

            if self._current == "\r":
                self.inc()

            if self._current == "\n":
                self.inc()

            if self._idx != self._marker or self._current.is_ws():
                trail = self.extract()

        return comment_ws, comment, trail

    def _parse_key_value(self, parse_comment: bool = False) -> Tuple[Key, Item]:
        # Leading indent
        self.mark()

        while self._current.is_spaces() and self.inc():
            pass

        indent = self.extract()

        # Key
        key = self._parse_key()

        self.mark()

        found_equals = self._current == "="
        while self._current.is_kv_sep() and self.inc():
            if self._current == "=":
                if found_equals:
                    raise self.parse_error(UnexpectedCharError, "=")
                else:
                    found_equals = True
        if not found_equals:
            raise self.parse_error(UnexpectedCharError, self._current)

        if not key.sep:
            key.sep = self.extract()
        else:
            key.sep += self.extract()

        # Value
        val = self._parse_value()
        # Comment
        if parse_comment:
            cws, comment, trail = self._parse_comment_trail()
            meta = val.trivia
            if not meta.comment_ws:
                meta.comment_ws = cws

            meta.comment = comment
            meta.trail = trail
        else:
            val.trivia.trail = ""

        val.trivia.indent = indent

        return key, val

    def _parse_key(self) -> Key:
        """
        Parses a Key at the current position;
        WS before the key must be exhausted first at the callsite.
        """
        if self._current in "\"'":
            return self._parse_quoted_key()
        else:
            return self._parse_bare_key()

    def _parse_quoted_key(self) -> Key:
        """
        Parses a key enclosed in either single or double quotes.
        """
        quote_style = self._current
        key_type = None
        dotted = False
        for t in KeyType:
            if t.value == quote_style:
                key_type = t
                break

        if key_type is None:
            raise RuntimeError("Should not have entered _parse_quoted_key()")

        self.inc()
        self.mark()

        while self._current != quote_style and self.inc():
            pass

        key = self.extract()

        if self._current == ".":
            self.inc()
            dotted = True
            key += "." + self._parse_key().as_string()
            key_type = KeyType.Bare
        else:
            self.inc()

        return Key(key, key_type, "", dotted)

    def _parse_bare_key(self) -> Key:
        """
        Parses a bare key.
        """
        key_type = None
        dotted = False

        self.mark()
        while (
            self._current.is_bare_key_char() or self._current.is_spaces()
        ) and self.inc():
            pass

        original = self.extract()
        key = original.strip()
        if not key:
            # Empty key
            raise self.parse_error(ParseError, "Empty key found")

        if " " in key:
            # Bare key with spaces in it
            raise self.parse_error(ParseError, f'Invalid key "{key}"')

        if self._current == ".":
            self.inc()
            dotted = True
            original += "." + self._parse_key().as_string()
            key = original.strip()
            key_type = KeyType.Bare

        return Key(key, key_type, "", dotted, original=original)

    def _handle_dotted_key(
        self, container: Union[Container, Table], key: Key, value: Any
    ) -> None:
        names = tuple(self._split_table_name(key.as_string()))
        name = names[0]
        name._dotted = True
        if name in container:
            if not isinstance(value, Table):
                table = Table(Container(True), Trivia(), False, is_super_table=True)
                _table = table
                for i, _name in enumerate(names[1:]):
                    if i == len(names) - 2:
                        _name.sep = key.sep

                        _table.append(_name, value)
                    else:
                        _name._dotted = True
                        _table.append(
                            _name,
                            Table(
                                Container(True),
                                Trivia(),
                                False,
                                is_super_table=i < len(names) - 2,
                            ),
                        )

                        _table = _table[_name]

                value = table

            container.append(name, value)

            return
        else:
            table = Table(Container(True), Trivia(), False, is_super_table=True)
            if isinstance(container, Table):
                container.raw_append(name, table)
            else:
                container.append(name, table)

        for i, _name in enumerate(names[1:]):
            if i == len(names) - 2:
                _name.sep = key.sep

                table.append(_name, value)
            else:
                _name._dotted = True
                if _name in table.value:
                    table = table.value[_name]
                else:
                    table.append(
                        _name,
                        Table(
                            Container(True),
                            Trivia(),
                            False,
                            is_super_table=i < len(names) - 2,
                        ),
                    )

                    table = table[_name]

    def _parse_value(self) -> Item:
        """
        Attempts to parse a value at the current position.
        """
        self.mark()
        c = self._current
        trivia = Trivia()

        if c == StringType.SLB.value:
            return self._parse_basic_string()
        elif c == StringType.SLL.value:
            return self._parse_literal_string()
        elif c == BoolType.TRUE.value[0]:
            return self._parse_true()
        elif c == BoolType.FALSE.value[0]:
            return self._parse_false()
        elif c == "[":
            return self._parse_array()
        elif c == "{":
            return self._parse_inline_table()
        elif c in "+-" or self._peek(4) in {
            "+inf",
            "-inf",
            "inf",
            "+nan",
            "-nan",
            "nan",
        }:
            # Number
            while self._current not in " \t\n\r#,]}" and self.inc():
                pass

            raw = self.extract()

            item = self._parse_number(raw, trivia)
            if item is not None:
                return item

            raise self.parse_error(InvalidNumberError)
        elif c in string.digits:
            # Integer, Float, Date, Time or DateTime
            while self._current not in " \t\n\r#,]}" and self.inc():
                pass

            raw = self.extract()

            m = RFC_3339_LOOSE.match(raw)
            if m:
                if m.group(1) and m.group(5):
                    # datetime
                    try:
                        dt = parse_rfc3339(raw)
                        return DateTime(
                            dt.year,
                            dt.month,
                            dt.day,
                            dt.hour,
                            dt.minute,
                            dt.second,
                            dt.microsecond,
                            dt.tzinfo,
                            trivia,
                            raw,
                        )
                    except ValueError:
                        raise self.parse_error(InvalidDateTimeError)

                if m.group(1):
                    try:
                        dt = parse_rfc3339(raw)
                        date = Date(dt.year, dt.month, dt.day, trivia, raw)
                        self.mark()
                        while self._current not in "\t\n\r#,]}" and self.inc():
                            pass

                        time_raw = self.extract()
                        if not time_raw.strip():
                            trivia.comment_ws = time_raw
                            return date

                        dt = parse_rfc3339(raw + time_raw)
                        return DateTime(
                            dt.year,
                            dt.month,
                            dt.day,
                            dt.hour,
                            dt.minute,
                            dt.second,
                            dt.microsecond,
                            dt.tzinfo,
                            trivia,
                            raw + time_raw,
                        )
                    except ValueError:
                        raise self.parse_error(InvalidDateError)

                if m.group(5):
                    try:
                        t = parse_rfc3339(raw)
                        return Time(
                            t.hour,
                            t.minute,
                            t.second,
                            t.microsecond,
                            t.tzinfo,
                            trivia,
                            raw,
                        )
                    except ValueError:
                        raise self.parse_error(InvalidTimeError)

            item = self._parse_number(raw, trivia)
            if item is not None:
                return item

            raise self.parse_error(InvalidNumberError)
        else:
            raise self.parse_error(UnexpectedCharError, c)

    def _parse_true(self):
        return self._parse_bool(BoolType.TRUE)

    def _parse_false(self):
        return self._parse_bool(BoolType.FALSE)

    def _parse_bool(self, style: BoolType) -> Bool:
        with self._state:
            style = BoolType(style)

            # only keep parsing for bool if the characters match the style
            # try consuming rest of chars in style
            for c in style:
                self.consume(c, min=1, max=1)

            return Bool(style, Trivia())

    def _parse_array(self) -> Array:
        # Consume opening bracket, EOF here is an issue (middle of array)
        self.inc(exception=UnexpectedEofError)

        elems: List[Item] = []
        prev_value = None
        while True:
            # consume whitespace
            mark = self._idx
            self.consume(TOMLChar.SPACES + TOMLChar.NL)
            indent = self._src[mark : self._idx]
            newline = set(TOMLChar.NL) & set(indent)
            if newline:
                elems.append(Whitespace(indent))
                continue

            # consume comment
            if self._current == "#":
                cws, comment, trail = self._parse_comment_trail(parse_trail=False)
                elems.append(Comment(Trivia(indent, cws, comment, trail)))
                continue

            # consume indent
            if indent:
                elems.append(Whitespace(indent))
                continue

            # consume value
            if not prev_value:
                try:
                    elems.append(self._parse_value())
                    prev_value = True
                    continue
                except UnexpectedCharError:
                    pass

            # consume comma
            if prev_value and self._current == ",":
                self.inc(exception=UnexpectedEofError)
                elems.append(Whitespace(","))
                prev_value = False
                continue

            # consume closing bracket
            if self._current == "]":
                # consume closing bracket, EOF here doesn't matter
                self.inc()
                break

            raise self.parse_error(UnexpectedCharError, self._current)

        try:
            res = Array(elems, Trivia())
        except ValueError:
            pass
        else:
            return res

    def _parse_inline_table(self) -> InlineTable:
        # consume opening bracket, EOF here is an issue (middle of array)
        self.inc(exception=UnexpectedEofError)

        elems = Container(True)
        trailing_comma = None
        while True:
            # consume leading whitespace
            mark = self._idx
            self.consume(TOMLChar.SPACES)
            raw = self._src[mark : self._idx]
            if raw:
                elems.add(Whitespace(raw))

            if not trailing_comma:
                # None: empty inline table
                # False: previous key-value pair was not followed by a comma
                if self._current == "}":
                    # consume closing bracket, EOF here doesn't matter
                    self.inc()
                    break

                if (
                    trailing_comma is False
                    or trailing_comma is None
                    and self._current == ","
                ):
                    # Either the previous key-value pair was not followed by a comma
                    # or the table has an unexpected leading comma.
                    raise self.parse_error(UnexpectedCharError, self._current)
            else:
                # True: previous key-value pair was followed by a comma
                if self._current == "}" or self._current == ",":
                    raise self.parse_error(UnexpectedCharError, self._current)

            key, val = self._parse_key_value(False)
            if key.is_dotted():
                self._handle_dotted_key(elems, key, val)
            else:
                elems.add(key, val)

            # consume trailing whitespace
            mark = self._idx
            self.consume(TOMLChar.SPACES)
            raw = self._src[mark : self._idx]
            if raw:
                elems.add(Whitespace(raw))

            # consume trailing comma
            trailing_comma = self._current == ","
            if trailing_comma:
                # consume closing bracket, EOF here is an issue (middle of inline table)
                self.inc(exception=UnexpectedEofError)

        return InlineTable(elems, Trivia())

    def _parse_number(self, raw: str, trivia: Trivia) -> Optional[Item]:
        # Leading zeros are not allowed
        sign = ""
        if raw.startswith(("+", "-")):
            sign = raw[0]
            raw = raw[1:]

        if (
            len(raw) > 1
            and raw.startswith("0")
            and not raw.startswith(("0.", "0o", "0x", "0b", "0e"))
        ):
            return

        if raw.startswith(("0o", "0x", "0b")) and sign:
            return

        digits = "[0-9]"
        base = 10
        if raw.startswith("0b"):
            digits = "[01]"
            base = 2
        elif raw.startswith("0o"):
            digits = "[0-7]"
            base = 8
        elif raw.startswith("0x"):
            digits = "[0-9a-f]"
            base = 16

        # Underscores should be surrounded by digits
        clean = re.sub(f"(?i)(?<={digits})_(?={digits})", "", raw)

        if "_" in clean:
            return

        if clean.endswith("."):
            return

        try:
            return Integer(int(sign + clean, base), trivia, sign + raw)
        except ValueError:
            try:
                return Float(float(sign + clean), trivia, sign + raw)
            except ValueError:
                return

    def _parse_literal_string(self) -> String:
        with self._state:
            return self._parse_string(StringType.SLL)

    def _parse_basic_string(self) -> String:
        with self._state:
            return self._parse_string(StringType.SLB)

    def _parse_escaped_char(self, multiline):
        if multiline and self._current.is_ws():
            # When the last non-whitespace character on a line is
            # a \, it will be trimmed along with all whitespace
            # (including newlines) up to the next non-whitespace
            # character or closing delimiter.
            # """\
            #     hello \
            #     world"""
            tmp = ""
            while self._current.is_ws():
                tmp += self._current
                # consume the whitespace, EOF here is an issue
                # (middle of string)
                self.inc(exception=UnexpectedEofError)
                continue

            # the escape followed by whitespace must have a newline
            # before any other chars
            if "\n" not in tmp:
                raise self.parse_error(InvalidCharInStringError, self._current)

            return ""

        if self._current in _escaped:
            c = _escaped[self._current]

            # consume this char, EOF here is an issue (middle of string)
            self.inc(exception=UnexpectedEofError)

            return c

        if self._current in {"u", "U"}:
            # this needs to be a unicode
            u, ue = self._peek_unicode(self._current == "U")
            if u is not None:
                # consume the U char and the unicode value
                self.inc_n(len(ue) + 1)

                return u

            raise self.parse_error(InvalidUnicodeValueError)

        raise self.parse_error(InvalidCharInStringError, self._current)

    def _parse_string(self, delim: StringType) -> String:
        # only keep parsing for string if the current character matches the delim
        if self._current != delim.unit:
            raise self.parse_error(
                InternalParserError,
                f"Invalid character for string type {delim}",
            )

        # consume the opening/first delim, EOF here is an issue
        # (middle of string or middle of delim)
        self.inc(exception=UnexpectedEofError)

        if self._current == delim.unit:
            # consume the closing/second delim, we do not care if EOF occurs as
            # that would simply imply an empty single line string
            if not self.inc() or self._current != delim.unit:
                # Empty string
                return String(delim, "", "", Trivia())

            # consume the third delim, EOF here is an issue (middle of string)
            self.inc(exception=UnexpectedEofError)

            delim = delim.toggle()  # convert delim to multi delim

        self.mark()  # to extract the original string with whitespace and all
        value = ""

        # A newline immediately following the opening delimiter will be trimmed.
        if delim.is_multiline() and self._current == "\n":
            # consume the newline, EOF here is an issue (middle of string)
            self.inc(exception=UnexpectedEofError)

        escaped = False  # whether the previous key was ESCAPE
        while True:
            code = ord(self._current)
            if (
                delim.is_singleline()
                and not escaped
                and (code == CHR_DEL or code <= CTRL_CHAR_LIMIT and code != CTRL_I)
            ):
                raise self.parse_error(InvalidControlChar, code, "strings")
            elif (
                delim.is_multiline()
                and not escaped
                and (
                    code == CHR_DEL
                    or code <= CTRL_CHAR_LIMIT
                    and code not in [CTRL_I, CTRL_J, CTRL_M]
                )
            ):
                raise self.parse_error(InvalidControlChar, code, "strings")
            elif not escaped and self._current == delim.unit:
                # try to process current as a closing delim
                original = self.extract()

                close = ""
                if delim.is_multiline():
                    # Consume the delimiters to see if we are at the end of the string
                    close = ""
                    while self._current == delim.unit:
                        close += self._current
                        self.inc()

                    if len(close) < 3:
                        # Not a triple quote, leave in result as-is.
                        # Adding back the characters we already consumed
                        value += close
                        continue

                    if len(close) == 3:
                        # We are at the end of the string
                        return String(delim, value, original, Trivia())

                    if len(close) >= 6:
                        raise self.parse_error(InvalidCharInStringError, self._current)

                    value += close[:-3]
                    original += close[:-3]

                    return String(delim, value, original, Trivia())
                else:
                    # consume the closing delim, we do not care if EOF occurs as
                    # that would simply imply the end of self._src
                    self.inc()

                return String(delim, value, original, Trivia())
            elif delim.is_basic() and escaped:
                # attempt to parse the current char as an escaped value, an exception
                # is raised if this fails
                value += self._parse_escaped_char(delim.is_multiline())

                # no longer escaped
                escaped = False
            elif delim.is_basic() and self._current == "\\":
                # the next char is being escaped
                escaped = True

                # consume this char, EOF here is an issue (middle of string)
                self.inc(exception=UnexpectedEofError)
            else:
                # this is either a literal string where we keep everything as is,
                # or this is not a special escaped char in a basic string
                value += self._current

                # consume this char, EOF here is an issue (middle of string)
                self.inc(exception=UnexpectedEofError)

    def _parse_table(
        self, parent_name: Optional[str] = None, parent: Optional[Table] = None
    ) -> Tuple[Key, Union[Table, AoT]]:
        """
        Parses a table element.
        """
        if self._current != "[":
            raise self.parse_error(
                InternalParserError, "_parse_table() called on non-bracket character."
            )

        indent = self.extract()
        self.inc()  # Skip opening bracket

        if self.end():
            raise self.parse_error(UnexpectedEofError)

        is_aot = False
        if self._current == "[":
            if not self.inc():
                raise self.parse_error(UnexpectedEofError)

            is_aot = True

        # Consume any whitespace
        self.mark()
        while self._current.is_spaces() and self.inc():
            pass

        ws_prefix = self.extract()

        # Key
        if self._current in [StringType.SLL.value, StringType.SLB.value]:
            delimiter = (
                StringType.SLL
                if self._current == StringType.SLL.value
                else StringType.SLB
            )
            name = self._parse_string(delimiter)
            name = "{delimiter}{name}{delimiter}".format(
                delimiter=delimiter.value, name=name
            )

            self.mark()
            while self._current != "]" and self.inc():
                if self.end():
                    raise self.parse_error(UnexpectedEofError)

                pass

            ws_suffix = self.extract()
            name += ws_suffix
        else:
            self.mark()
            while self._current != "]" and self.inc():
                if self.end():
                    raise self.parse_error(UnexpectedEofError)

                pass

            name = self.extract()

        name = ws_prefix + name

        if not name.strip():
            raise self.parse_error(EmptyTableNameError)

        key = Key(name, sep="")
        name_parts = tuple(self._split_table_name(name))
        if any(" " in part.key.strip() and part.is_bare() for part in name_parts):
            raise self.parse_error(ParseError, f'Invalid table name "{name}"')

        missing_table = False
        if parent_name:
            parent_name_parts = tuple(self._split_table_name(parent_name))
        else:
            parent_name_parts = tuple()

        if len(name_parts) > len(parent_name_parts) + 1:
            missing_table = True

        name_parts = name_parts[len(parent_name_parts) :]

        values = Container(True)

        self.inc()  # Skip closing bracket
        if is_aot:
            # TODO: Verify close bracket
            self.inc()

        cws, comment, trail = self._parse_comment_trail()

        result = Null()
        table = Table(
            values,
            Trivia(indent, cws, comment, trail),
            is_aot,
            name=name_parts[0].key if name_parts else key.key,
            display_name=name,
        )

        if len(name_parts) > 1:
            if missing_table:
                # Missing super table
                # i.e. a table initialized like this: [foo.bar]
                # without initializing [foo]
                #
                # So we have to create the parent tables
                table = Table(
                    Container(True),
                    Trivia(indent, cws, comment, trail),
                    is_aot and name_parts[0].key in self._aot_stack,
                    is_super_table=True,
                    name=name_parts[0].key,
                )

                result = table
                key = name_parts[0]

                for i, _name in enumerate(name_parts[1:]):
                    if _name in table:
                        child = table[_name]
                    else:
                        child = Table(
                            Container(True),
                            Trivia(indent, cws, comment, trail),
                            is_aot and i == len(name_parts) - 2,
                            is_super_table=i < len(name_parts) - 2,
                            name=_name.key,
                            display_name=name if i == len(name_parts) - 2 else None,
                        )

                    if is_aot and i == len(name_parts) - 2:
                        table.raw_append(
                            _name, AoT([child], name=table.name, parsed=True)
                        )
                    else:
                        table.raw_append(_name, child)

                    table = child
                    values = table.value
        else:
            if name_parts:
                key = name_parts[0]

        while not self.end():
            item = self._parse_item()
            if item:
                _key, item = item
                if not self._merge_ws(item, values):
                    if _key is not None and _key.is_dotted():
                        self._handle_dotted_key(table, _key, item)
                    else:
                        table.raw_append(_key, item)
            else:
                if self._current == "[":
                    is_aot_next, name_next = self._peek_table()

                    if self._is_child(name, name_next):
                        key_next, table_next = self._parse_table(name, table)

                        table.raw_append(key_next, table_next)

                        # Picking up any sibling
                        while not self.end():
                            _, name_next = self._peek_table()

                            if not self._is_child(name, name_next):
                                break

                            key_next, table_next = self._parse_table(name, table)

                            table.raw_append(key_next, table_next)

                    break
                else:
                    raise self.parse_error(
                        InternalParserError,
                        "_parse_item() returned None on a non-bracket character.",
                    )

        if isinstance(result, Null):
            result = table

            if is_aot and (not self._aot_stack or name != self._aot_stack[-1]):
                result = self._parse_aot(result, name)

        return key, result

    def _peek_table(self) -> Tuple[bool, str]:
        """
        Peeks ahead non-intrusively by cloning then restoring the
        initial state of the parser.

        Returns the name of the table about to be parsed,
        as well as whether it is part of an AoT.
        """
        # we always want to restore after exiting this scope
        with self._state(save_marker=True, restore=True):
            if self._current != "[":
                raise self.parse_error(
                    InternalParserError,
                    "_peek_table() entered on non-bracket character",
                )

            # AoT
            self.inc()
            is_aot = False
            if self._current == "[":
                self.inc()
                is_aot = True

            self.mark()

            table_name = ""
            while self._current != "]" and self.inc():
                table_name = self.extract()

            return is_aot, table_name

    def _parse_aot(self, first: Table, name_first: str) -> AoT:
        """
        Parses all siblings of the provided table first and bundles them into
        an AoT.
        """
        payload = [first]
        self._aot_stack.append(name_first)
        while not self.end():
            is_aot_next, name_next = self._peek_table()
            if is_aot_next and name_next == name_first:
                _, table = self._parse_table(name_first)
                payload.append(table)
            else:
                break

        self._aot_stack.pop()

        return AoT(payload, parsed=True)

    def _peek(self, n: int) -> str:
        """
        Peeks ahead n characters.

        n is the max number of characters that will be peeked.
        """
        # we always want to restore after exiting this scope
        with self._state(restore=True):
            buf = ""
            for _ in range(n):
                if self._current not in " \t\n\r#,]}":
                    buf += self._current
                    self.inc()
                    continue

                break
            return buf

    def _peek_unicode(self, is_long: bool) -> Tuple[Optional[str], Optional[str]]:
        """
        Peeks ahead non-intrusively by cloning then restoring the
        initial state of the parser.

        Returns the unicode value is it's a valid one else None.
        """
        # we always want to restore after exiting this scope
        with self._state(save_marker=True, restore=True):
            if self._current not in {"u", "U"}:
                raise self.parse_error(
                    InternalParserError, "_peek_unicode() entered on non-unicode value"
                )

            self.inc()  # Dropping prefix
            self.mark()

            if is_long:
                chars = 8
            else:
                chars = 4

            if not self.inc_n(chars):
                value, extracted = None, None
            else:
                extracted = self.extract()

                if extracted[0].lower() == "d" and extracted[1].strip("01234567"):
                    return None, None

                try:
                    value = chr(int(extracted, 16))
                except (ValueError, OverflowError):
                    value = None

            return value, extracted
