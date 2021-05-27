
g = {"__version__": None}
with open("../src/rezup/_version.py") as f:
    exec(f.read(), g)

__version__ = g["__version__"]
