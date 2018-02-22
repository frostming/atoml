from setuptools import setup
import io
import os
from atoml import __version__


def readme():
    content = io.open(os.path.join(os.path.dirname(__file__), 'README.rst'),
                      encoding='utf-8')
    return content


setup(
    name='atoml',
    description='A python toml decoder and encoder',
    long_description=readme(),
    version=__version__,
    author='Frost Ming',
    author_email='mianghong@gmail.com',
    url='',
    packages=['atoml'],
)