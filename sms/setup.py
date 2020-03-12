#!/usr/bin/env python
from setuptools import find_packages, setup

setup(
    name='mybnbaid-sms',
    version='0.0.1',
    description='Mybnbaid sms microservice',
    packages=find_packages(exclude=['test', 'test.*']),
    entry_points={
        'console_scripts': ['mybnbaid.sms=sms.service:main']
    },
    install_requires=[
        'rock==0.0.1'
        'pyzmq==18.1.0',
        'tornado==6.0.3'
    ],
    include_package_data=True,
    extras_require={
        'dev': [
            'pytest==3.1.1',
            'coverage==4.4.1',
            'flake8==3.3.0'
        ]
    },
    zip_safe=True
)
