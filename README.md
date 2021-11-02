# rezup

[![Python package](https://github.com/davidlatwe/rezup/actions/workflows/python-package.yml/badge.svg)](https://github.com/davidlatwe/rezup/actions/workflows/python-package.yml)
[![Version](http://img.shields.io/pypi/v/rezup-api.svg?style=flat)](https://pypi.python.org/pypi/rezup-api)

[Rez](https://github.com/nerdvegas/rez) launching environment manager

<img src="https://user-images.githubusercontent.com/3357009/130851292-2510bb0e-7fc5-409e-bfbb-e38ab4086d11.gif" width="610"></img>


### What is this ?

A cross-platform Rez production virtual environment management tool, which allows safe environment update without any interruption. Plus a convenient virtual environment setup interface.

## Install

This installs the `rezup` full package.
```
$ pip install rezup
```
To **upgrade**, you only need to upgrade the API part. So to avoid re-creating console-script.
```
$ pip install -U rezup-api
```

## Quick start
```shell
$ rezup
```
What will/should happen ?
1. For first time quick-start, run `rezup` will create a default container `.main` under `~/.rezup`
2. Wait for it...
3. Bam! A vanilla Rez environment is presented (In subprocess)
4. Try `rez --version`
5. Once you're done, simply type `exit` to escape.


## Commands
Please run `rezup --help` or `rezup [COMMAND] --help` for each command's usage.
```shell
$ rezup --help
$ rezup use --help  
```

## How it works ?

### Container

A *container* is a Rez environment. And each container holds at least one virtual environment folder named by timestamp, which is *revision*. With that convention, the latest version of environment can be provided without affecting existing user.

```
# Container/Revision structure

\.rezup
   |
   + - {container}
   |     |
   :     + - {revision}  # venv and bin tools lives here
   :     |
         + - {revision}  # the folder is named as timestamp, e.g. 1619780350.588625
         |
         + - {revision}  # latest one will be provided when calling `rezup use {container}` in terminal

```

For centralize management in production, one remote container can be defined with env var `REZUP_ROOT_REMOTE`. The remote container only contains the venv installation manifest file `rezup.toml`, and when being asked, a venv revision will be created locally or re-used if same revision exists in local.


### Recipe

To customize the container, you can write a `~/rezup.toml` to tell what should be installed and what environment variable should have. For example :

```toml
description = "My rez setup"

[root]
# Where local container is at, supersede $REZUP_ROOT_LOCAL if set
local = false
# Where remote container is at, supersede $REZUP_ROOT_REMOTE if set
remote = false

# the .env file will be loaded when container revision is being used
[dotenv]
1 = "/to/my.env"    # non platform specific, load firstly, sort by key
2 = "/to/other.env"
[dotenv.linux]
[dotenv.darwin]
[dotenv.windows]
a = "/to/win.env"   # platform specific, load secondly, sort by key

[env]
# these will be loaded when container revision is being used
REZ_CONFIG_FILE = "/path/to/rezconfig.py"
MY_CUSTOMS_ENV = "my value"

[rez]
name = "rez"
url = "rez>=2.83"   # a PyPi version specifier or repository path

[[extension]]
name = "foo"
url = "~/dev/foo"
edit = true         # install this in edit mode (pip --edit)

[[extension]]
name = "bar"
url = "git+git://github.com/get-bar/bar"
isolation = true    # additional venv will be created just for this package
python = 2.7        # the python version for the venv of this package

[shared]
# Packages that will be shared across all revisions in this container,
# except extension that has `isolated` set to true.
name = "production"
requires = [
    "toml",
    "pyside2",
    "Qt5.py",
]

```

Recipe file name should embed container name (if not default container) so that command `rezup add <container>` could pick it up when creating corresponding container, for example:

* `~/rezup.toml` for container `.main`, the default
* `~/rezup.dev.toml` for container `dev`
* `~/rezup.test.toml` for container `test`
* `~/rezup.{name}.toml` for container `{name}`


## Environment Variables

|Name|Description|
| --- | --- |
|REZUP_ROOT_LOCAL|Local root of all containers and metadata, default is `~/.rezup`|
|REZUP_ROOT_REMOTE|Remote root of all containers but only recipe file|
|REZUP_DEFAULT_SHELL|Specify shell to use. See [launch/README](src/rezup/launch/README.md#shell-detection).|
|REZUP_PROMPT|For customizing shell prompt, optional. See [launch/README](src/rezup/launch/README.md#shell-prompt).|
|REZUP_CONTAINER|Auto set, for customizing shell prompt. See [launch/README](src/rezup/launch/README.md#shell-prompt).|
|REZUP_USING_REMOTE|Auto set, indicating where the container was sourced from.|
|REZUP_TEST_KEEP_TMP|Preserve temp dirs in tests.|


## Shell

Please read [launch/README](src/rezup/launch/README.md).


## Util

```python
from rezup import util

# returns rez lib location from container
util.locate_rez_lib()

# resolve package requests with Rez from container
util.resolve_environ(["pkg_a", "pkg_b"])

```
