#!/usr/bin/env python3

from setuptools import find_packages, setup

with open('README.rst', 'r') as fp:
    long_description = fp.read()

setup(
    name='djangorestframework-dataclasses',
    version='0.2',
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
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Typing :: Typed'
    ],
    packages=find_packages(),
    python_requires='>=3.7',
    install_requires=[
        'django>=1.11',
        'djangorestframework>=3.9'
    ]
)
