#!/usr/bin/env python
from setuptools import find_packages, setup

setup(
    name='mybnbaid-mail',
    version='0.0.1',
    description='Mybnbaid mail microservice',
    packages=find_packages(exclude=['test', 'test.*']),
    entry_points={
        'console_scripts': ['mybnbaid.mail=mail.service:main']
    },
    install_requires=[
        'rock==0.0.1',
    ],
    extras_require={
        'dev': [
            'pytest>=3.1.1',
            'coverage>=4.4.1',
            'flake8>=3.3.0'
        ]
    },
    zip_safe=True
)
