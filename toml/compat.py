"""
    toml.compat
    ~~~~~~~~~~~~
    Python 2/3 compatibility

    :author: Frost Ming
    :email: mianghong@gmail.com
    :license: BSD-2
"""
# flake8: noqa
import sys

if sys.version_info[0] == 3:    # PY3
    unichr = chr
    basestring = (str, bytes)
    long = int
    unicode = str
    from io import StringIO
else:   # PY2
    basestring = basestring
    unichr = unichr
    long = long
    unicode = unicode
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO