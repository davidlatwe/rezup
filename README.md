# rezup

[![Python package](https://github.com/davidlatwe/rezup/actions/workflows/python-package.yml/badge.svg)](https://github.com/davidlatwe/rezup/actions/workflows/python-package.yml)
[![Version](http://img.shields.io/pypi/v/rezup-api.svg?style=flat)](https://pypi.python.org/pypi/rezup-api)

A cross-platform [Rez](https://github.com/nerdvegas/rez) production tooling manager

<img src="https://user-images.githubusercontent.com/3357009/130851292-2510bb0e-7fc5-409e-bfbb-e38ab4086d11.gif" width="610"></img>

[Read The Docs](https://davidlatwe.github.io/rezup/)


## Why use rezup

* Easier to setup/update Rez venv
* Easier to install custom Rez extensions (plugins)
* Easier to provide different Rez venv setup for different purpose


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

Simply calling `rezup` in terminal will suffice.

```shell
$ rezup
```

The command above is a shorthand for `rezup use .main`, which means to enter a Rez venv container named `.main`. Usually you must `rezup add` a new container before you can use it. But default container `.main` will automatically be created if it's not existing yet, for the first time.

So, what will & should happen after calling `rezup` ?

1. A most basic recipe will be written into user home directory (`~/rezup.toml`)
2. Default container `.main` will be created with that recipe
3. Wait for it...
4. Bam! A vanilla Rez environment is presented (In subprocess)
5. Try `rez --version` or any `rez` command
6. Once you're done, simply type `exit` to escape.

As you may have seen, Rez venv is in the container and is deployed with a recipe file. Please visit [Container-Recipe](https://davidlatwe.github.io/rezup/container/#recipe) page for more detail about how you can auth and create a richer container by the recipe.

And for other rezup commands, please run `rezup --help` or `rezup [COMMAND] --help` for each command's usage.

```shell
$ rezup --help
```

Or, visit [Command](https://davidlatwe.github.io/rezup/command/) page.
