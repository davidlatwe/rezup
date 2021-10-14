# rezup

[![Python package](https://github.com/davidlatwe/rezup/actions/workflows/python-package.yml/badge.svg)](https://github.com/davidlatwe/rezup/actions/workflows/python-package.yml)
[![Version](http://img.shields.io/pypi/v/rezup-api.svg?style=flat)](https://pypi.python.org/pypi/rezup-api)

[Rez](https://github.com/nerdvegas/rez) launching environment manager

<img src="https://user-images.githubusercontent.com/3357009/130851292-2510bb0e-7fc5-409e-bfbb-e38ab4086d11.gif" width="610"></img>


### What is this ?

A Rez production virtual environment management tool, which allows safe environment update without any interruption. Plus a convenient virtual environment setup interface.

## Install

```
# python 3+
$ pip install rezup
```

## Quick start

By typing `rezup` in terminal, a container named `.main` will be created under `~/.rezup` by default (the root location can be changed by setting env var `REZUP_ROOT_LOCAL`). Once that done, a vanilla Rez environment is presented by a subprocess and simply typing `exit` to escape.

### Container

A *container* is a Rez environment. And each container holds at least one virtual environment folder named by timestamp, which is *revision*. With that convention, latest version of environment can be provided without affecting existing user.

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

[env]
REZ_CONFIG_FILE = "/path/to/rezconfig.py"

```
Section `env` is for setting environment variables when container revision is being used. However, this feature can be hard to debug when something goes wrong, because it's per revision setting and currently no tool for iterating those `.toml` between revisions for debug. See [Site Customize](#site-customize) below for better alternative.

Recipe file name should embed container name (if not default container) so that command `rezup add <container>` could pick it up when creating corresponding container, for example:

* `~/rezup.toml` for container `.main`, the default
* `~/rezup.dev.toml` for container `dev`
* `~/rezup.test.toml` for container `test`
* `~/rezup.{name}.toml` for container `{name}`


### Caveat

Rez production install validation will failed, due to Rezup manages entrypoints a bit like [pipx](https://github.com/pipxproject/pipx), which is different from the setup of Rez install script. So e.g. `rez-env` can not nesting context (rez bin tools will not be appended in `PATH`), without [changing](https://github.com/davidlatwe/rez/commit/4bc4729c73ab61294cfb8fda24b4b9cf1b060e08) production install validation mechanism.


## Commands

use default container `.main`
```
$ rezup
```

use foo
```
$ rezup use foo
```

use foo and do job
```
$ rezup use foo --do {script.bat or "quoted command"}
```

create & use new venv into default container `.main` (recipe `~/rezup.toml` will be used)
```
$ rezup add
```

create & use new venv into container foo (recipe `~/rezup.foo.toml` will be used)
```
$ rezup add foo
```

create new venv into default remote container
```
$ rezup add --remote --skip-use
```

remove container foo
```
$ rezup drop foo
```

list containers and info
```
$ rezup status
```


## Auto Upgrade

Updating package that has running console scripts can be error prone. We need to separate API package and CLI scripts as two different PyPI project (`rezup-api` & `rezup`), so we can safely upgrade only the package part while the console script is running.

Both projects will be released together under same version, so that one could still upgrading the API part via upgrading CLI. As long as console script is not in use.

```
pip install --upgrade rezup
```

The upgrade checking process will be triggered immediately when calling `rezup` in console, except version querying or last upgrade check is done not long before `REZUP_UPGRADE_PAUSE` period ends. If upgrade is needed and completed, session will be restarted with previous command.

To disable auto upgrade, use command flag `--no-upgrade` or set env var `REZUP_NO_UPGRADE` with any value.


## Environment Variables

|Name|Description|
| --- | --- |
|REZUP_ROOT_LOCAL|Local root of all containers and metadata, default is `~/.rezup`|
|REZUP_ROOT_REMOTE|Remote root of all containers but only recipe file|
|REZUP_NO_UPGRADE|Disable auto upgrade if set (any value is valid except empty string)|
|REZUP_UPGRADE_PAUSE|Pause version check after last upgrade, default 86400 (1 day, in second)|
|REZUP_UPGRADE_SOURCE|Local source repository for upgrade, check from PyPI if not set.|
|REZUP_PROMPT|For customizing shell prompt, optional.|


## Shell

Please read [launch/README](src/rezup/launch/README.md).


## Site Customize

You could set a python script file in `~/rezup.toml` like so

```toml
# ~/rezup.toml
[init]
script = "/path/to/script.py"
```

If set, the script will be executed immediately on rezup launch. Which means, all the operations will be affected by that script. This also enabled to provide different setup base on username or other arguments.

Current use case is to load and set environment variables.

```python
# /path/to/script.py
import os
from dotenv import load_dotenv
load_dotenv(os.path.splitext(__file__)[0] + ".env")
```
