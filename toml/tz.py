"""
    toml-py.tz
    ~~~~~~~~~~
    The time zone class for date time

    :author: Frost Ming
    :email: mianghong@gmail.com
    :license: BSD-2
"""
from datetime import tzinfo, timedelta


class TomlTZ(tzinfo):
    def __init__(self, tz_str):
        if tz_str == "Z":
            self._raw_offset = "+00:00"
        else:
            self._raw_offset = tz_str
        self._sign = -1 if self._raw_offset[0] == '-' else 1
        self._hours = int(self._raw_offset[1:3])
        self._minutes = int(self._raw_offset[4:6])

    def tzname(self, dt):
        return 'UTC' + self._raw_offset

    def utcoffset(self, dt):
        return self._sign * timedelta(hours=self._hours, minutes=self._minutes)

    def dst(self, dt):
        return timedelta(0)
