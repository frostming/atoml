"""
    toml.encoder
    ~~~~~~~~~~~~
    TOML encoder

    :author: Frost Ming
    :email: mianghong@gmail.com
    :license: BSD-2
"""
import re
from contextlib import contextmanager
from datetime import date, datetime, time

from atoml.compat import IS_PY3, StringIO, basestring, long, unicode
from atoml.errors import TomlEncodeError

if not IS_PY3:
    str = unicode   # noqa

_escapes = {'\n': '\\n', '\r': '\\r', '\\': '\\\\', '\t': '\\t',
            '\b': '\\b', '\f': '\\f', '"': '\\"'}

class Encoder(object):
    """Encoder class to represent objects as string

    :param outstream: a string object to be parsed
    :param indent_incr: the indent increment inside a table array block
    """
    # conversion handlers, use tuple list to preserve the order
    lookup_dict = [
        ('string', basestring),
        ('bool', bool),
        ('integer', (int, long)),
        ('datetime', datetime),
        ('time', time),
        ('date', date),
        ('list', (tuple, list)),
        ('table', dict),
        ('float', float),
    ]

    def __init__(self, outstream, indent_incr=2):
        self.indent_incr = indent_incr
        self._indent = ''
        self.outstream = outstream

    @contextmanager
    def indent(self, preceding=None):
        if preceding is None:
            preceding = self._indent + self.indent_incr * ' '
        old_indent = self._indent
        self._indent = preceding
        yield
        self._indent = old_indent

    def represent(self, obj):
        for name, types in Encoder.lookup_dict:
            if isinstance(obj, types):
                func = getattr(self, 'represent_%s' % name,
                               self.represent_default)
                return func(obj)
        return self.represent_default(obj)

    def represent_default(self, obj):
        return str(obj)

    def represent_bool(self, obj):
        return str(obj).lower()

    def represent_float(self, obj):
        return repr(obj)

    def represent_datetime(self, obj):
        return obj.isoformat().replace('+00:00', 'Z')

    def represent_date(self, obj):
        return obj.strftime('%Y-%m-%d')

    def represent_time(self, obj):
        return obj.strftime('%H:%M:%S.%f')

    def represent_list(self, obj):
        return '[ ' + ', '.join(self.represent(item) for item in obj) + ' ]'

    def represent_string(self, obj):
        s = str(obj)
        start = 0
        i = 0
        res = []

        def flush():
            if start < i:
                res.append(s[start:i])
            return i + 1

        while i < len(s):
            c = s[i]
            if c in _escapes:
                start = flush()
                res.append(_escapes[c])
            elif ord(c) < 0x20:
                start = flush()
                res.append('\\u%04x' % ord(c))
            i += 1

        flush()
        return '"' + ''.join(res) + '"'

    def write_dict(self, obj, header=None):
        header = header or []
        sub_tables = []
        table_arrays = []
        for k, v in obj.items():
            if isinstance(v, dict):
                sub_tables.append(k)
            elif isinstance(v, list) and _is_table_array(v):
                table_arrays.append(k)
            else:
                self._write('%s%s = %s\n' % (
                    self._indent,
                    _table_header([k]),
                    self.represent(v),
                ))

        for table in sub_tables:
            self._write('\n')
            self._write('%s[%s]\n\n' % (self._indent, _table_header(header + [table])))
            self.write_dict(obj[table], header + [table])

        for array in table_arrays:
            for item in obj[array]:
                self._write('\n')
                self._write(
                    '%s[[%s]]\n\n' % (self._indent, _table_header(header + [array])))
                with self.indent():
                    self.write_dict(item, header + [array])

    def _write(self, string):
        # if not IS_PY3 and isinstance(string, unicode):
        #     string = string.encode('utf-8')
        self.outstream.write(string)


def _table_header(headers):
    headers = headers or []
    rv = []
    for key in headers:
        if not re.match(r'^[a-zA-Z0-9_\-]+$', key):
            rv.append('"%s"' % key.replace('"', '\\"'))
        else:
            rv.append(key)
    return '.'.join(rv)


def _is_table_array(obj):
    if not obj:
        return True
    if len(obj) > 1 and type(obj[0]) != type(obj[1]):
        raise TomlEncodeError('Cannot dump array of different types')
    return isinstance(obj[0], dict)


def dump(obj, f):
    """Write dict object into file

    :param obj: the object to be dumped into toml
    :param f: the file object
    """
    if not f.write:
        raise TypeError('You can only dump an object into a file object')
    encoder = Encoder(f)
    return encoder.write_dict(obj)


def dumps(obj):
    """Stringifies a dict as toml

    :param obj: the object to be dumped into toml
    """
    f = StringIO()
    dump(obj, f)
    return f.getvalue()
