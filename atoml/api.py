import collections
import io
import pkgutil

import lark

from atoml.containers import Container
from atoml.transformer import TOMLTransformer

EBNF_SPEC = pkgutil.get_data(__name__, "toml.lark").decode("utf-8")


def parse(toml_string: str) -> Container:
    parser = lark.Lark(EBNF_SPEC)
    tree = parser.parse(toml_string)
    return TOMLTransformer().transform(tree)


def loads(data: str) -> Container:
    return parse(data)


def load(fp: io.TextIOWrapper) -> Container:
    return parse(fp.read())


def dumps(data: collections.abc.Mapping) -> str:
    if not isinstance(data, Container):
        c = Container()
        c.update(data)
    else:
        c = data
    return c.serialize()


def dump(data: collections.abc.Mapping, fp: io.TextIOWrapper) -> None:
    fp.write(dumps(data))
