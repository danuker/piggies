#!/usr/bin/env python3

from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='piggies',
    version='0.0.1',
    description='A package to automatically manage cryptocurrency wallets',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/danuker/piggies',
    license='MIT',
    author='Dan Gheorghe Haiduc',
    author_email='danuthaiduc@gmail.com',
    python_requires='>=3.5',
    packages=['piggies'],
    install_requires=['jsonrpclib-pelix', 'web3', 'pyetherchain', 'pexpect'],
    test_suite='nose.collector',
    tests_require=['nose'],
    classifiers=(
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Unix",
    ),
)
