# rezup

[![Python package](https://github.com/davidlatwe/rezup/actions/workflows/python-package.yml/badge.svg)](https://github.com/davidlatwe/rezup/actions/workflows/python-package.yml)
[![Version](http://img.shields.io/pypi/v/rezup-api.svg?style=flat)](https://pypi.python.org/pypi/rezup-api)

A cross-platform [Rez](https://github.com/nerdvegas/rez) production tooling manager

<img src="https://user-images.githubusercontent.com/3357009/130851292-2510bb0e-7fc5-409e-bfbb-e38ab4086d11.gif" width="610"></img>


## Why use rezup

* Simplify Rez venv setup and update process
* Easier to manage Rez tooling


## Install

This installs the `rezup` full package, command line tool and the api package.

```shell
$ pip install rezup
```

To **upgrade**, you only need to upgrade the api package. So to avoid re-creating console-script.

```shell
$ pip install -U rezup-api
```

## Quick start

Call `rezup` in your terminal

```shell
$ rezup
```

What will/should happen ?

1. For first time quick-start, calling `rezup` will create a default container
2. So wait for it...
3. Bam! A vanilla Rez environment is presented (In subprocess)
4. Try `rez --version` or any `rez` command
5. Once you're done, simply type `exit` to escape.

To know more, please run `rezup --help` or `rezup [COMMAND] --help` for each command's usage.

```shell
$ rezup --help
```

Or, [Read The Docs](https://davidlatwe.github.io/rezup/)
