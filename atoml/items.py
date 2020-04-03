from __future__ import annotations

import ast
import collections
import numbers
from typing import Optional, Union, List, Iterator, Any


class _Item:
    def __init__(self, children: Optional[List[Item]] = None) -> None:
        self.children = children or []

    def serialize(self) -> str:
        return "".join(serialize(p) for p in self.children)


Item = Union[_Item, str]


def serialize(obj: Item) -> str:
    return getattr(obj, "serialize", lambda x=obj: str(x))()


class BasicString(_Item, collections.UserString, str):
    def __init__(self, args: List[Item]) -> None:
        super().__init__(args)
        collections.UserString.__init__(self, "".join(map(str, args)))

    def __repr__(self) -> str:
        return repr(str(self))

    def serialize(self) -> str:
        return f'"{super().serialize()}"'


class LiteralString(_Item, collections.UserString, str):
    def __init__(self, args: List[Item]) -> None:
        super().__init__(args)
        collections.UserString.__init__(self, "".join(map(str, args)))

    def __repr__(self) -> str:
        return repr(str(self))

    def serialize(self) -> str:
        return f"'{super().serialize()}'"


class Expression(_Item):
    @property
    def keyval(self) -> Optional[KeyVal]:
        return next(
            iter(child for child in self.children if isinstance(child, KeyVal)), None
        )


class TableHead(_Item):
    pass


class Separator(_Item):
    def __init__(self, sep, spaces):
        super().__init__([spaces[0], sep, spaces[1]])


class KeyVal(_Item):

    def __init__(self, k: Item, v: Item, sep: str = " = ") -> None:
        super().__init__([k, sep, v])

    @property
    def key(self) -> str:
        return str(self.children[0])

    @property
    def value(self) -> Item:
        return self.children[2]

    @value.setter
    def value(self, data: Item) -> None:
        self.children[2] = data


class DottedKey(_Item):

    def __iter__(self) -> Iterator[str]:
        for child in self.children:
            if not isinstance(child, Separator):
                yield str(child)


class Escaped(_Item, collections.UserString, str):
    def __init__(self, escape_char: str) -> None:
        super().__init__(["\\", escape_char])
        collections.UserString.__init__(self, ast.literal_eval(f'"\\{escape_char}"'))


class Boolean(_Item, int):
    def __init__(self, value: bool) -> None:
        super().__init__(["true"] if value else ["false"])
        self.value = value

    def __bool__(self) -> bool:
        return self.value

    def __int__(self) -> int:
        return int(self.value)

    def serialize(self) -> str:
        return self.children[0]

    def __repr__(self) -> str:
        return repr(self.value)

    def __str__(self) -> str:
        return str(self.value)
