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

IS_PY3 = sys.version_info[0] == 3

if IS_PY3:    # PY3
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
    # cStringIO doesn't support unicode input
    # So have to use StringIO
    from StringIO import StringIO
