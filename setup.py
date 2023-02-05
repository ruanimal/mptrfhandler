from setuptools import setup, find_packages
from mptrfhandler import __author__, __version__

from os import path
this_directory = path.abspath(path.dirname(__file__))

with open(path.join(this_directory, 'requirements.txt')) as f:
    requirements = f.read().splitlines()

with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()
print(requirements, long_description)
setup(
    name='mptrfhandler',
    version=__version__,
    author=__author__,
    author_email=__author__,
    description='支持按时间滚动的Python多进程日志Handler',
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'Programming Language :: Python :: 3',
    ],
    # critical configurations.
    packages=find_packages(exclude=["tests"]),
    py_modules=[
        "mptrfhandler",
    ],
    install_requires=requirements,
    project_urls={
        'Source': 'https://github.com/ruanimal/mptrfhandler',
    },
)
