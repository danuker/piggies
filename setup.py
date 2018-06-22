from setuptools import setup

setup(
    name='piggies',
    version='0.0.1',
    description='A package to automatically manage your cryptocurrency wallets.',
    url='https://github.com/danuker/piggies',
    license='MIT',
    author='Dan Gheorghe Haiduc',
    author_email='danuthaiduc@gmail.com',
    packages=['piggies'],
    install_requires=['jsonrpclib', 'web3'],
    test_suite='nose.collector',
    tests_require=['nose']
)
