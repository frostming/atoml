import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import toml
import pprint


def test():
    content = open(os.path.join(os.path.dirname(__file__), 'test_normal.toml')).read()
    pprint.pprint(toml.loads(content))


def main():
    pass


if __name__ == '__main__':
    test()
