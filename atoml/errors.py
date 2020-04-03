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
    pass


class TomlEncodeError(TomlError):
    pass
