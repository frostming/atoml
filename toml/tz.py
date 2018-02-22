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

    @staticmethod
    def represent_tz(tzinfo):
        if not tzinfo:
            return 'Z'
        offset = tzinfo.utcoffset(None)
        sign = '+'
        if offset.total_seconds() < 0:
            offset = -offset
            sign = '-'
        hours = offset.seconds // 3600
        minutes = (offset.seconds % 3600) // 60
        return '%s%02d:%02d' % (sign, hours, minutes)
