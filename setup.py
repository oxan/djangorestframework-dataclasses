#!/usr/bin/env python3

import os
from setuptools import find_packages, setup

with open('README.rst', 'r') as fp:
    long_description = fp.read()

# FIXME The tests need this, but setting it here seems ugly.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.django_settings")

setup(
    name='djangorestframework-dataclasses',
    version='0.6',
    description='A dataclasses serializer for Django REST Framework',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    url='https://github.com/oxan/djangorestframework-dataclasses',
    author='Oxan van Leeuwen',
    author_email='oxan@oxanvanleeuwen.nl',
    license='BSD',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Typing :: Typed'
    ],
    packages=find_packages(),
    package_data={
        'rest_framework_dataclasses': ['py.typed']
    },
    python_requires='>=3.7',
    install_requires=[
        'django>=2.0',
        'djangorestframework>=3.9',
        'typing_extensions>=3.7.4; python_version<"3.8"'
    ]
)
