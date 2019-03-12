import os
import json
import re
import datetime
import pytest
import atoml as toml
from atoml.compat import basestring, long
from atoml.tz import TomlTZ

TEST_DIR = os.path.join(os.path.dirname(__file__), 'toml-test', 'tests')
SUPPORTED_TYPES = ('string', 'integer', 'float', 'datetime', 'bool', 'array')


def convert_datetime(datestring):
    match = re.match(r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})'
                     r'(\.\d{6})?(Z|[+-]\d{2}:\d{2})?', datestring)
    date_string = match.group(1).replace('T', ' ')
    dt = datetime.datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S')
    if match.group(2):
        dt = dt.replace(microsecond=int(match.group(2)[1:]))
    if match.group(3):
        dt = dt.replace(tzinfo=TomlTZ(match.group(3)))
    return dt


def tag(value):
    if isinstance(value, dict):
        rv = {}
        for k, v in value.items():
            rv[k] = tag(v)
        return rv
    elif isinstance(value, list):
        rv = []
        for v in value:
            rv.append(tag(v))
        if rv and 'value' not in rv[0]:
            return rv
        return {'type': 'array', 'value': rv}
    elif isinstance(value, basestring):
        return {'type': 'string', 'value': value}
    elif isinstance(value, bool):
        return {'type': 'bool', 'value': str(value).lower()}
    elif isinstance(value, (int, long)):
        return {'type': 'integer', 'value': str(value)}
    elif isinstance(value, float):
        return {'type': 'float', 'value': repr(value)}
    elif isinstance(value, datetime.datetime):
        return {'type': 'datetime', 'value': value.isoformat().replace('+00:00', 'Z')}
    raise ValueError('Unknown type: %s' % type(value))


def untag(value):
    if isinstance(value, list):
        return [untag(v) for v in value]
    if set(value.keys()) != {'type', 'value'}:
        d = dict()
        for k, v in value.items():
            d[k] = untag(v)
        return d
    t, v = value['type'], value['value']
    if t == 'array':
        return [untag(i) for i in v]
    elif t == 'string':
        return v
    elif t == 'integer':
        return long(v)
    elif t == 'float':
        return float(v)
    elif t == 'bool':
        return v == 'true'
    elif t == 'datetime':
        return convert_datetime(v)
    else:
        raise ValueError('Value type is not supported: %r' % t)


def list_dir(subdir, postfix='.toml'):
    dirpath = os.path.join(TEST_DIR, subdir)
    assert os.path.isdir(dirpath)
    rv = []
    for path in os.listdir(dirpath):
        if path.endswith(postfix):
            rv.append((dirpath, path[:-len(postfix)]))
    return rv


@pytest.mark.parametrize('dirname,name', list_dir('valid'))
def test_valid(dirname, name):
    toml_file = os.path.join(dirname, name + '.toml')
    json_file = os.path.join(dirname, name + '.json')
    decoded = toml.load(open(toml_file))
    golden = untag(json.load(open(json_file)))
    encoded = toml.dumps(decoded)
    decoded2 = toml.loads(encoded)
    assert decoded == golden, "Decoded result is not equal to golden: %s" % name
    assert decoded2 == golden, "Decoded encoded result is not equal to golden: %s" % name


@pytest.mark.parametrize('dirname,name', list_dir('invalid'))
def test_invalid_decode(dirname, name):
    toml_file = os.path.join(dirname, name + '.toml')
    with pytest.raises(Exception):
        toml.load(open(toml_file))


@pytest.mark.parametrize('dirname,name', list_dir('invalid-encoder', '.json'))
def test_invalid_encode(dirname, name):
    json_file = os.path.join(dirname, name + '.json')
    with pytest.raises(Exception):
        toml.dumps(untag(json.load(open(json_file))))
