
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
