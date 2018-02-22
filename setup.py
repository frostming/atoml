from setuptools import setup
import codecs
import os
from atoml import __version__


def readme():
    content = codecs.open(os.path.join(os.path.dirname(__file__),
                                       'README.rst'),
                          encoding='utf-8').read()
    return content


setup(
    name='atoml',
    description='A python toml decoder and encoder',
    long_description=readme(),
    version=__version__,
    author='Frost Ming',
    author_email='mianghong@gmail.com',
    url='https://github.com/frostming/atoml',
    packages=['atoml'],
    license='BSD-2',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: PyPy',
    ]
)
