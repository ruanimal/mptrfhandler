from setuptools import setup, find_packages
from mptrfhandler import __author__, __version__

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='mptrfhandler',
    version=__version__,
    author=__author__,
    author_email=__author__,
    description='支持按时间滚动的Python多进程日志Handler',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'Programming Language :: Python :: 3.5',
    ],
    # critical configurations.
    packages=find_packages(exclude=["tests"]),
    py_modules=[
        "mptrfhandler",
    ],
    install_requires=requirements,
)
