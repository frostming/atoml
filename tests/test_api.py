import os
import json
import datetime
import atoml
import pytest
from atoml.compat import basestring, long

TEST_DIR = os.path.join(os.path.dirname(__file__), 'toml-test', 'tests')
SUPPORTED_TYPES = ('string', 'integer', 'float', 'datetime', 'bool', 'array')
# These tests are no longer valid in TOML v0.4.0
IGNORE_TESTS = [
    'string-bad-byte-escape',
    'string-bad-escape',
    'string-byte-escapes'
]


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
        return [untag(i) for i in v['value']]
    elif t == 'string':
        return v
    elif t == 'integer':
        return long(v)
    elif t == 'float':
        return float(v)
    elif t == 'bool':
        return v == 'true'
    elif t == 'datetime':
        return datetime.datetime.strptime(v, '%Y-%m-%dT%H:%M:%SZ')
    else:
        raise ValueError('Value type is not supported: %r' % t)


def list_dir(subdir, postfix='.toml'):
    dirpath = os.path.join(TEST_DIR, subdir)
    assert os.path.isdir(dirpath)
    rv = []
    for path in os.listdir(dirpath):
        if path.endswith(postfix):
            if path[:-len(postfix)] in IGNORE_TESTS:
                continue
            rv.append((dirpath, path[:-len(postfix)]))
    return rv


@pytest.mark.parametrize('dirname,name', list_dir('valid'))
def test_valid(dirname, name):
    toml_file = os.path.join(dirname, name + '.toml')
    json_file = os.path.join(dirname, name + '.json')
    decoded = atoml.load(open(toml_file))
    golden = untag(json.load(open(json_file)))
    encoded = atoml.dumps(decoded)
    decoded2 = atoml.loads(encoded)
    assert decoded == golden, "Decoded result is not equal to golden: %s" % name
    assert decoded2 == golden, "Decoded encoded result is not equal to golden: %s" % name


@pytest.mark.parametrize('dirname,name', list_dir('invalid'))
def test_invalid_decode(dirname, name):
    toml_file = os.path.join(dirname, name + '.toml')
    with pytest.raises(ValueError):
        atoml.load(open(toml_file))


@pytest.mark.parametrize('dirname,name', list_dir('invalid-encoder'))
def test_invalid_encode(dirname, name):
    json_file = os.path.join(dirname, name + '.json')
    with pytest.raises(ValueError):
        atoml.dump(untag(json.load(open(json_file))))
