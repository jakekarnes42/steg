from setuptools import setup, find_packages

setup(
    name='steg',
    version='0.0.1',
    packages=find_packages(),
    include_package_data=True,
    url='https://github.com/jakekarnes42/steg',
    license='MIT',
    author='Jake Karnes',
    author_email='jake.karnes@gmail.com',
    description='An exploration into Steganography',
    py_modules=['steg'],
    install_requires=[
        'Click', 'Pillow', 'bitarray'
    ],
    entry_points='''
        [console_scripts]
        steg=steg.scripts.cli:cli
    ''',
)
