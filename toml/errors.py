"""
    toml.encoder
    ~~~~~~~~~~~~
    TOML encoder

    :author: Frost Ming
    :email: mianghong@gmail.com
    :license: BSD-2
"""


class TomlError(ValueError):
    pass


class TomlDecodeError(TomlError):
    def __init__(self, lineno, message):
        self.lineno = lineno
        self.message = message

    def __str__(self):
        return 'Line %d: %s' % (self.lineno, self.message)


class TomlEncodeError(TomlError):
    pass
