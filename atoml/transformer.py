from __future__ import annotations

import pkgutil
from typing import List, Callable

import lark
from lark import v_args

from atoml.containers import Container, Table, InlineTable, ArrayTable
from atoml.errors import TomlDecodeError
from atoml.items import Expression, KeyVal, Separator, BasicString, \
    DottedKey, LiteralString, Escaped, Boolean, TableHead


def raw(coerce: bool = False) -> Callable:
    @v_args(True)
    def f(self, arg):
        if coerce:
            return str(arg)
        return arg
    return f


class TOMLTransformer(lark.Transformer):

    wschar = raw(True)

    def ws(self, args):
        return ''.join(args)

    @v_args(True)
    def newline(self, args):
        self.state.add_item(str(args))
        return str(args)

    non_ascii = raw(True)
    non_eol = raw(True)
    LETTER = DIGIT = HEXDIGIT = raw(True)

    def comment(self, args):
        return '#' + ''.join(args)

    def unquoted_key(self, args):
        return ''.join(args)

    def literal_string(self, args):
        return LiteralString(args[1:-1])

    def escape_seq_char(self, args):
        return "".join(args)

    digit_sep = lambda _, x: "_"
    minus = lambda _, x: "-"
    plus = lambda _, x: "+"
    inf = lambda _, x: "inf"
    nan = lambda _, x: "nan"

    def unsigned_dec_int(self, args):
        return "".join(args)

    dec_int = float_exp_part = special_float = unsigned_dec_int

    def hex_int(self, args):
        return "0x" + "".join(args)

    def oct_int(self, args):
        return "0o" + "".join(args)

    def bin_int(self, args):
        return "0b" + "".join(args)

    def exp(self, args):
        return "e" + "".join(args)

    def frac(self, args):
        return "." + "".join(args)

    basic_unescaped = raw(True)

    @v_args(True)
    def escaped(self, _, seq):
        return Escaped(seq)

    basic_char = raw()
    literal_char = raw()

    def dot_sep(self, args):
        return Separator(".", args)

    def keyval_sep(self, args):
        return Separator("=", args)

    def basic_string(self, args):
        return BasicString(args[1:-1])

    def dotted_key(self, args):
        return DottedKey(args)

    quoted_key = raw()
    simple_key = raw()
    key = raw()
    string = raw()
    val = raw()

    def expression(self, args):
        self.state.add_item(Expression(args))
        return Expression(args)

    table = raw()

    @v_args(True)
    def std_table_open(self, args):
        return '[' + args

    @v_args(True)
    def std_table_close(self, args):
        return args + ']'

    @v_args(True)
    def array_table_open(self, args):
        return '[[' + args

    @v_args(True)
    def array_table_close(self, args):
        return args + ']]'

    @v_args(True)
    def inline_table_open(self, args):
        return '{' + args

    @v_args(True)
    def inline_table_close(self, args):
        return args + '}'

    def inline_table_sep(self, args):
        return Separator(',', args)

    def true(self, args):
        return Boolean(True)

    def inline_table_keyvals(self, args):
        return args

    def false(self, args):
        return Boolean(False)

    def unicode(self, args):
        return "u" + "".join(args)

    def big_unicode(self, args):
        return "U" + "".join(args)

    boolean = raw()

    def std_table(self, args):
        keys = args[1]
        if not isinstance(keys, DottedKey):
            keys = [keys]
        else:
            keys = list(keys)
        while not self.state.is_parent(keys):
            self.pop_state()

        for i in range(len(self.state.heads), len(keys)):
            if keys[i] in self.state:
                child = self.state[keys[i]]
                if isinstance(child, list):
                    child = child[-1]
            elif i < len(keys) - 1:
                child = Table(keys[:i + 1], intermediate=True)
                self.state.add_item(child)
            else:
                break
            self.push_state(child)
        if self.state.heads == keys:
            if isinstance(self.state, ArrayTable):
                raise TomlDecodeError(
                    f"Not allowed to assign different table type for {keys}"
                )
            self.pop_state()
        current = Table(keys)
        self.state.add_item(current)
        self.push_state(current)
        return TableHead(args)

    def inline_table(self, args):
        return InlineTable(*args)

    def array_table(self, args):
        keys = args[1]
        if not isinstance(keys, DottedKey):
            keys = [keys]
        else:
            keys = list(keys)
        while not self.state.is_parent(keys):
            self.pop_state()

        for i in range(len(self.state.heads), len(keys)):
            if keys[i] in self.state:
                child = self.state[keys[i]]
                if isinstance(child, list):
                    child = child[-1]
            elif i < len(keys) - 1:
                child = Table(keys[:i + 1], intermediate=True)
                self.state.add_item(child)
            else:
                break
            self.push_state(child)
        if self.state.heads == keys:
            if isinstance(self.state, Table):
                raise TomlDecodeError(
                    f"Not allowed to assign different table type for {keys}"
                )
            self.pop_state()
        current = ArrayTable(keys)
        self.state.add_item(current)
        self.push_state(current)
        return TableHead(args)

    @v_args(True)
    def keyval(self, k, sep, v):
        return KeyVal(k, v, sep)

    def toml(self, args):
        return self.root

    def __init__(self, visit_tokens=True):
        super().__init__(visit_tokens)
        self.root = Container()
        self._states: List[Container] = [self.root]

    @property
    def state(self) -> Container:
        try:
            return self._states[-1]
        except IndexError:
            raise TomlDecodeError("Illegal document")

    def push_state(self, state: Container) -> None:
        self._states.append(state)

    def pop_state(self) -> Container:
        return self._states.pop()
