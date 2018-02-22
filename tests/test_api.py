import sys
import os
import json
import datetime
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import toml     # noqa: E402
from toml.compat import basestring, long

SUPPORTED_TYPES = ('string', 'integer', 'float', 'datetime', 'bool', 'array')


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
    if isinstance(value, dict):
        if set(value.keys()) == {'type', 'value'} and value['type'] in SUPPORTED_TYPES:
            return untag(value['value'])
        d = {}
        for k, v in value.items():
            d[k] = untag(v)
        return d
    elif isinstance(value, list):
        return [untag(v) for v in value]
    else:
        return value


if __name__ == '__main__':
    if sys.argv[-1] == '-encode':
        input_data = json.loads(sys.stdin.read())
        print(json.dumps(toml.dumps(untag(input_data))))
    else:
        res = toml.loads(sys.stdin.read())
        print(json.dumps(tag(res)))
