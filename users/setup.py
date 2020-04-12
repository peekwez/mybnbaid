#!/usr/bin/env python
from setuptools import find_packages, setup

setup(
    name='mybnbaid-users',
    version='0.0.1',
    description='Mybnbaid users microservice',
    packages=find_packages(exclude=['test', 'test.*']),
    entry_points={
        'console_scripts': [
            'mybnbaid.users=users.service:main',
        ]

    },
    install_requires=[
        'backless==0.0.1',
    ],
    package_data={'users': ['emails/*.txt', 'emails/*.html']},
    extras_require={
        'dev': [
            'pytest>=3.1.1',
            'coverage>=4.4.1',
            'flake8>=3.3.0'
        ]
    },
    zip_safe=True
)
