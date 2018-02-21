import sys
import os
import pprint
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import toml     # noqa: E402

here = os.path.dirname(__file__)


def test():
    content = open(
        os.path.join(here, 'test_value.toml'),
        # '/Users/fming/wkspace/github/flaskblog/Pipfile',
        'r').read()
    pprint.pprint(toml.loads(content))


def main():
    pass


if __name__ == '__main__':
    test()
