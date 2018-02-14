import sys
import os
import pprint
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import toml     # noqa: E402


def test():
    content = open(
        os.path.join(os.path.dirname(__file__), 'test_value.toml'),
        'rb').read()
    pprint.pprint(toml.loads(content))


def main():
    pass


if __name__ == '__main__':
    test()
