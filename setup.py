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

# data_files property is used for normal install and package_data is used for wheel installs
setup(
    name='chp_learn',
    version=__version__,
    author='Chase Yakaboski',
    author_email='chase.th@dartmouth.edu',
    description='Learned relationships database for the Connections Hypothesis Provider',
    packages=find_packages(),
    data_files=[
        ('',
            [
                'chp_learn/curies_database.json',
                'chp_learn/meta_knowledge_graph.json',
                ]
            )
        ],
    package_data={'chp_learn': ['curies_database.json', 'meta_knowledge_graph.json']},
    install_requires=REQUIRED_PACKAGES,
    python_requires='>=3.8',
    zip_safe=True,
)
