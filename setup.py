
from setuptools import setup, find_packages


__version__ = ""
exec(open("src/rezup/_version.py").read())

setup(
    name="rezup",
    version=__version__,
    author="davidlatwe",
    author_email="davidlatwe@gmail.com",
    package_dir={"": "src"},
    packages=find_packages("src"),
    entry_points={
        "console_scripts": ["rezup = rezup.cli:run"],
    },
    requires=[
        "distlib",
        "entrypoints",
    ]
)
