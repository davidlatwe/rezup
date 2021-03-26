
from setuptools import setup, find_packages


__version__ = ""
with open("src/rezup/_version.py") as f:
    exec(f.read())
with open("README.md") as f:
    long_description = f.read()

setup(
    name="rezup",
    version=__version__,
    description="Rez launching environment manager",
    keywords="package resolve version build install software management",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/davidlatwe/rezup",
    author="davidlatwe",
    author_email="davidlatwe@gmail.com",
    license="GPLv3",
    package_dir={"": "src"},
    packages=find_packages("src"),
    entry_points={
        "console_scripts": ["rezup = rezup.cli:run"],
    },
    install_requires=[
        "distlib",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development",
        "Topic :: System :: Software Distribution"
    ]
)
