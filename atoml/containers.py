from __future__ import annotations

import collections
import itertools
from typing import List, Iterator, Any, Dict, Optional

from atoml.items import Expression, Item, _Item, KeyVal, Separator, TableHead, serialize


class Container(_Item, collections.abc.MutableMapping, dict):
    def __init__(self) -> None:
        super().__init__()
        self.heads: List[str] = []   # Top document has not heads
        self._key_map: Dict[str, Item] = {}

    def is_parent(self, keys: List[str]) -> bool:
        return keys[:len(self.heads)] == self.heads

    def rel_key(self, keys: List[str]) -> List[str]:
        return keys[len(self.heads):]

    def itemize(self, key: str, value: Any) -> _Item:
        if not isinstance(value, _Item):
            if isinstance(value, collections.abc.Mapping):
                item = Table([])
                item.update(value)
            elif isinstance(value, collections.abc.MutableSequence):
                item = []
            else:
                return Expression(["", KeyVal(key, value)])
        else:
            item = value

        assert isinstance(value, Container)
        # Must by table or AoT
        if getattr(item, "heads", None):
            item.heads = self.heads + [key]
            item.intermediate = False
        return item

    def add_item(self, item: Item) -> None:
        """An item can be one of [Expression, newline, table, array-of-table]"""
        self.children.append(item)
        if isinstance(item, Expression) and item.keyval:
            self._key_map[item.keyval.key] = item
        elif hasattr(item, "heads"):
            direct_key = self.rel_key(item.heads)[0]
            if isinstance(item, ArrayTable):
                self._key_map.setdefault(direct_key, []).append(item)
            else:
                prev = self._key_map.get(direct_key)
                if prev:
                    assert hasattr(
                        prev, "connect"
                    ), "Only standard tables can be continued."
                    self._key_map[direct_key] = prev.connect(item)
                else:
                    self._key_map[direct_key] = item

    def __setitem__(self, k: str, v: Any) -> None:
        try:
            item = self._key_map[k]
            if isinstance(item, Expression) and item.keyval:
                item.keyval.value = v
            else:
                idx = self.children.index(item)
                self.children[idx] = self._key_map[k] = self.itemize(k, v)
        except KeyError:
            item = self.itemize(k, v)
            self.add_item(item)

    def __delitem__(self, k: str) -> None:
        item = self._key_map.pop(k)
        idx = self.children.index(item)
        del self.children[idx]
        if idx <= len(self.children) and isinstance(self.children[idx - 1], str):
            # Also delete the preceding newline if there is any.
            del self.children[idx - 1]

    def __getitem__(self, k: str) -> Any:
        item = self._key_map[k]
        if getattr(item, "keyval", None):
            return item.keyval.value
        return item

    def __len__(self) -> int:
        return len(self._key_map)

    def __iter__(self) -> Iterator[str]:
        return iter(self._key_map)

    def __str__(self) -> str:
        return str({k: v for k, v in self.items()})

    def __repr__(self) -> str:
        return str(self)


class Table(Container):

    def __init__(
        self, heads: Optional[List[str]] = None, intermediate: bool = False
    ) -> None:
        super().__init__()
        self.heads: List[str] = heads or []
        self._table_head = None
        self.intermediate = intermediate

    def connect(self, table: "Table") -> ContinuousTable:
        return ContinuousTable([self, table])

    def add_item(self, item: Item) -> None:
        super().add_item(item)
        if isinstance(item, Expression) and any(
            isinstance(p, TableHead) for p in item.children
        ):
            self._table_head = item

    @property
    def table_head(self) -> Expression:
        if self._table_head:
            return self._table_head
        return Expression(["[", ".".join(self.heads), "]"])

    def serialize(self) -> str:
        children = (
            self.children
            if self._table_head or self.intermediate
            else [self.table_head, "\n"] + self.children
        )
        return "".join(serialize(p) for p in children)


class ArrayTable(Table):
    @property
    def table_head(self):
        if self._table_head:
            return self._table_head
        return Expression(["[[", ".".join(self.heads), "]]"])


class ContinuousTable(Container):
    """Tables can be defined continuously in the TOML document.
    If the same key exists in multiple sources, the latter takes precedence.

    Example:
        [package]
        foo = "bar"

        [metadata]
        name = "John"

        [package]   # 'package table' continues here
        hello = "world"
    """

    def __init__(self, tables: List[Table]) -> None:
        super().__init__()
        self.tables = tables

    def connect(self, table: Table) -> "ContinuousTable":
        self.tables.append(table)
        return self

    def add_item(self, item: Item) -> None:
        self.tables[-1].add_item(item)

    def __getitem__(self, k: str) -> Any:
        for table in self.tables[::-1]:
            try:
                return table[k]
            except KeyError:
                pass
        raise KeyError(k)

    def __setitem__(self, k: str, v: Any) -> None:
        for table in self.tables[::-1]:
            if k in table:
                table[k] = v
                return
        self.tables[-1][k] = v

    def __delitem__(self, k: str) -> None:
        for table in self.tables[::-1]:
            if k in table:
                del table[k]
                return
        raise KeyError(k)

    def __iter__(self) -> Iterator[str]:
        return iter(set(itertools.chain.from_iterable(self.tables)))

    def __len__(self):
        return len(set(itertools.chain.from_iterable(self.tables)))


class InlineTable(_Item, collections.abc.MutableMapping, dict):
    def __init__(
        self, open: str = "{", keyvals: Optional[List[Item]] = None, close: str = "}"
    ):
        keyvals = keyvals or []
        super().__init__([open, *keyvals, close])
        self._key_map = {
            item.key: item for item in self.children if isinstance(item, KeyVal)
        }

    def __setitem__(self, k: str, v: Any) -> None:
        if isinstance(v, (Container, InlineTable)):
            raise ValueError(
                "Can't assign a container or inline table to an inline table value."
            )
        try:
            item = self._key_map[k]
            item.value = v
        except KeyError:
            item = KeyVal(k, v)
            sep = Separator(",", ["", " "])
            if len(self.children):
                self.children.extend([sep, item])
            else:
                self.children.append(item)

    def __delitem__(self, v: str) -> None:
        item = self._key_map.pop(v)
        idx = self.children.index(item)
        del self.children[idx]
        # also delete the preceding separator
        if idx <= len(self.children) and isinstance(self.children[idx - 1], Separator):
            del self.children[idx - 1]

    def __getitem__(self, k: str) -> Any:
        return self._key_map[k].value

    def __len__(self) -> int:
        return len(self._key_map)

    def __iter__(self) -> Iterator[str]:
        return iter(self._key_map)

    def __str__(self) -> str:
        return str({k: v for k, v in self.items()})

    def __repr__(self) -> str:
        return str(self)
