
from setuptools import setup


g = {"__version__": ""}
with open("../src/rezup/_version.py") as f:
    exec(f.read(), g)
__version__ = g["__version__"]

setup(
    version=__version__,
    install_requires=["rezup-api>=%s,<2" % __version__]
)
