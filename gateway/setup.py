#!/usr/bin/env python
from setuptools import find_packages, setup

setup(
    name='mybnbaid-gateway',
    version='0.0.1',
    description='Mybnbaid gateway microservice',
    packages=find_packages(exclude=['test', 'test.*']),
    entry_points={
        'console_scripts': ['mybnbaid.gateway=gateway.service:main']
    },
    install_requires=[
        'backless==0.0.1',
        'tornado>=6.0.3',
    ],
    include_package_data=True,
    extras_require={
        'dev': [
            'pytest>=3.1.1',
            'coverage>=4.4.1',
            'flake8>=3.3.0'
        ]
    },
    zip_safe=True
)
