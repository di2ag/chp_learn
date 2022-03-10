import os
import sys
import re
import io

from setuptools import find_packages
from setuptools import setup

__version__ = '1.0'

REQUIRED_PACKAGES = [
        'compress_pickle[lz4]',
        'tqdm',
        'django',
        'django-extensions',
        'numpy',
        'pandas',
]

setup(
    name='chp_learn',
    version=__version__,
    author='Chase Yakaboski',
    author_email='chase.th@dartmouth.edu',
    description='Learned relationships database for the Connections Hypothesis Provider',
    packages=find_packages(),
    install_requires=REQUIRED_PACKAGES,
    python_requires='>=3.8',
)
