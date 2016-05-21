"""Setup for jim.

Derived from https://github.com/pypa/sampleproject

"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path
from glob import glob

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'DESCRIPTION.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='jim',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='1.1.2',

    description='JIm = Jim Improved, Score Processing System for ATTTC Club',
    long_description=long_description,
    url='http://bitbucket.com/tbd',
    author='Ilija Hadzic',
    author_email='ilijahadzic@gmail.com',
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Tennis Players',
        'Topic :: Applications :: Web',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    keywords='tennis rankings competition database web',
    packages=find_packages(exclude=[]),
    install_requires=['tornado', 'bcrypt', 'python-daemon', 'argparse'],
    package_data={
        'jim': ['jim.cfg']
    },
    data_files=[
        ('var/jim/html', glob('html/*')),
        ('var/jim/templates', glob('templates/*')),
        ('var/jim/certs', glob('certs/*'))
    ],
    entry_points={
        'console_scripts': [
            'jim=jim:main',
        ],
    },
)
