import os
import sys
import atoml
from pprint import pprint
from test_api import tag, TEST_DIR


def main(name):
    toml_file = os.path.join(TEST_DIR, 'valid', name + '.toml')
    rv = atoml.load(open(toml_file))
    encoded = atoml.dumps(rv)
    pprint(rv)
    pprint(tag(rv))
    pprint(encoded)


if __name__ == '__main__':
    main(sys.argv[1])
