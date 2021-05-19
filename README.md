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

Each container holds at least one virtual environment folder which are named by timestamp. With that convention, latest version of environment can be provided without affecting existing user. (`Container`/`Revision` structure)

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
