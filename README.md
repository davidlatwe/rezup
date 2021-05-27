# rezup

[Rez](https://github.com/nerdvegas/rez) launching environment manager


### What is this ?

A Rez production virtual environment management tool, which allows safe environment update without any interruption. Plus a convenient virtual environment setup interface.


### Install

```
# python 3+
$ pip install rezup
```


### Usage

By typing `rezup` in terminal, a container named `.main` will be created under `~/.rezup` by default, the root location can be changed by setting env var `REZUP_ROOT_LOCAL`. Once that command is done, vanilla Rez environment is presented by a subprocess and simply typing `exit` to escape.

Each container holds at least one virtual environment folder which are named by timestamp. With that convention, latest version of environment can be provided without affecting existing user.

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

To customize environment, you can write a `~/rezup.toml` to tell what should be installed and what environment variable should have. For example :

```toml
description = "My rez setup"

[rez]
name = "rez"
url = "rez>=2.83"

[[extension]]
name = "foo"
url = "~/dev/foo"
edit = true

[[extension]]
name = "bar"
url = "git+git://github.com/get-bar/bar"
isolation = true
python = 2.7

[env]
REZ_CONFIG_FILE = "/path/to/rezconfig.py"

```

The settings in section `rez` and `extension` will be parsed and pass to `pip`, so the `url` can be e.g. a version specifier and the package will be installed from PyPi.

The `edit` can be used if the `url` is a filesystem path that point to the source code and the Rez environment can run in dev-mode.

If the extension has `isolation` set to true, additional venv will be created just for that package. Different Python version (if can be found from system) will be used when `python` entry presented.


### Caveat

Rez production install validation will failed, due to Rezup manages entrypoints a bit like [pipx](https://github.com/pipxproject/pipx), which is different from the setup of Rez install script. So e.g. `rez-env` can not nesting context (rez bin tools will not be appended in `PATH`), without [changing](https://github.com/davidlatwe/rez/commit/4bc4729c73ab61294cfb8fda24b4b9cf1b060e08) production install validation mechanism.


### Commands

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
$ rezup use foo --do {script.bat}
```

create new venv into default container (`~/rezup.toml` will be picked)
```
$ rezup use --make
```

create new venv into container foo (`~/rezup.toml` will be picked)
```
$ rezup use foo --make
```

create new venv into default container with specific `rezup.toml`
```
$ rezup use --make {rezup.toml}
```

remove container foo
```
$ rezup drop foo
```

list containers
```
$ rezup list
```


### Auto Upgrade

Updating package that has running console scripts can be error prone. We need to separate API package and CLI scripts as two different PyPI project (`rezup-api` & `rezup`), so we can safely upgrade only the package part while the console script is running.

Both projects will be released together under same version, so that one could still upgrading the API part via upgrading CLI. As long as console script is not in use.

```
pip install --upgrade rezup
```

The upgrade checking process will be triggered immediately when calling `rezup` in console, except version querying or last upgrade check is done not long before `REZUP_UPGRADE_PAUSE` period ends. If upgrade is needed and completed, session will be restarted with previous command.


### Environment Variables

|Name|Description|
| --- | --- |
|REZUP_ROOT_LOCAL|Local root of all containers and metadata, default is `~/.rezup`|
|REZUP_ROOT_REMOTE|Remote root of all containers but only recipe file|
|REZUP_NO_UPGRADE|Disable auto upgrade if set (any value is valid except empty string)|
|REZUP_UPGRADE_PAUSE|Pause version check after last upgrade, default 86400 (1 day, in second)|
|REZUP_UPGRADE_SOURCE|Local source repository for upgrade, check from PyPI if not set.|
