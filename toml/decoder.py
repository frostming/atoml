"""
    toml.decoder
    ~~~~~~~~~~~~
    TOML decoder

    :author: Frost Ming
    :email: mianghong@gmail.com
    :license: BSD-2
"""
import re
import sys
import shlex

from toml.errors import TomlDecodeError

if sys.version_info[0] == 3:
    unichr = chr
    basestring = str
    long = int
    from io import StringIO
else:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO


def contains_list(longer, shorter):
    """Check if longer list starts with shorter list"""
    if len(longer) <= len(shorter):
        return False
    for a, b in zip(shorter, longer):
        if a != b:
            return False
    return True


def cut_list(longer, shorter):
    shorter = shorter or []
    """Cut the longer list with the shorter one"""
    return longer[len(shorter):]


def split_string(string, splitter=','):
    lex = shlex.shlex(string, posix=True)
    lex.whitespace += splitter
    lex.whitespace_split = True
    return list(lex)


KEY_VALUE_RE = re.compile(r'^\s*([\'"])?'
                          r'(?P<key>(?(1)(?!\1).|[^\s\'"=])+)'
                          r'(?(1)\1)'
                          r'\s*=\s*(?P<value>.*)$', flags=re.DOTALL)
BLANK_RE = re.compile(r'^\s*(#.*)?$')
TABLE_RE = re.compile(r'^\s*\[([^\[\]]+)\]\s*(#.*)?$')
TABLE_ARRAY_RE = re.compile(r'^\s*\[{2}([^\[\]]+)\]{2}\s*(#.*)?$')


class Decoder(object):

    def __init__(self, instream, dict_=dict):
        self.dict_ = dict_
        self.data = self.dict_()
        if isinstance(instream, basestring):
            instream = StringIO(instream)
        self.instream = instream
        self.lineno = 0

    def parse(self, data=None, table_name=None):
        """Parse the lines from index i

        :param data: optional, store the parsed result to it when specified
        :param table_name: when inside a table array, it is the table array name
        """
        temp = self.dict_()
        sub_table = None
        is_array = False
        line = ''
        while True:
            line = self.instream.readline()
            self.lineno += 1
            if not line:
                self._store_table(sub_table, temp, data=data)
                break       # EOF
            if BLANK_RE.match(line):
                continue
            if TABLE_RE.match(line):
                table = split_string(TABLE_RE.match(line).group(1), '.')
                if table_name and not contains_list(table, table_name):
                    self._store_table(sub_table, temp, data=data)
                    break
                table = cut_list(table, table_name)
                if sub_table == table:
                    raise TomlDecodeError(self.lineno, 'Duplicate table name'
                                          'in origin: %r' % sub_table)
                else:       # different table name
                    self._store_table(sub_table, temp, data=data)
                    sub_table = table
            elif TABLE_ARRAY_RE.match(line):
                table = split_string(TABLE_ARRAY_RE.match(line).group(1), '.')
                if table_name and not contains_list(table, table_name):
                    # Out of current loop
                    # write current data dict to table dict
                    self._store_table(sub_table, temp, data=data)
                    break
                table = cut_list(table, table_name)
                if sub_table == table and not is_array:
                    raise TomlDecodeError(self.lineno, 'Duplicate name of '
                                          'table and array of table: %r'
                                          % sub_table)
                else:   # Begin a nested loop
                    # Write any temp data to table dict
                    self._store_table(sub_table, temp, data=data)
                    sub_table = (table_name or []) + table
                    is_array = True
                    self.parse(temp, (table_name or []) + table)
                    # `data` in nested loop is `temp` in current context
                    # Store the data of nested loop to current table dict
                    self._store_table(table, temp, True, data)
            elif KEY_VALUE_RE.match(line):
                res = KEY_VALUE_RE.match(line).groupdict()
                key, value = res['key'], res['value']
                if key in temp:
                    raise TomlDecodeError(self.lineno,
                                          'Duplicate key %r' % key)
                temp[key] = self._parse_value(value)
            else:
                raise TomlDecodeError(self.lineno,
                                      'Parsing error: %r' % line)
        # Rollback to the last line for next parse
        # This will do nothing if EOF is hit
        self.instream.seek(-len(line), 1)
        self.lineno -= 1

    def _store_table(self, table_name, table, is_array=False, data=None):
        if not table:
            return
        if data is None:
            data = self.data
        if table_name:
            for name in table_name[:-1]:
                data = data.setdefault(name, self.dict_())
                if not isinstance(data, self.dict_):
                    raise TomlDecodeError(self.lineno,
                                          'Not a dict: %r' % name)
            name = table_name[-1]
            if is_array:
                data = data.setdefault(name, [])
                if not isinstance(data, list):
                    raise TomlDecodeError(self.lineno,
                                          'Not a list: %r' % name)
                data.append(table.copy())
                table.clear()
                return
            else:
                data = data.setdefault(name, self.dict_())
                if not isinstance(data, self.dict_):
                    raise TomlDecodeError(self.lineno,
                                          'Not a dict: %r' % name)
        for k, v in table.items():
            if k in data:
                raise TomlDecodeError(self.lineno,
                                      'Duplicate key %r' % k)
            else:
                data[k] = v
        table.clear()

    def _parse_value(self, value):
        return value.strip()


def load(f, dict_=dict):
    if not hasattr(f, 'readline'):
        raise ValueError('The first parameter needs to be a file object, ',
                         '%r is passed' % type(f))
    decoder = Decoder(f, dict_)
    decoder.parse()
    return decoder.data


def loads(content, dict_=dict):
    if not isinstance(content, basestring):
        raise ValueError('The first parameter needs to be a string object, ',
                         '%r is passed' % type(f))
    return load(StringIO(content), dict_)
