
from setuptools import setup


g = {"__version__": ""}
with open("../src/rezup/_version.py") as f:
    exec(f.read(), g)
__version__ = g["__version__"]

setup(
    version=__version__,
)
