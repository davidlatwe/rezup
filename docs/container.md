
## Structure

A *container* provides Rez environment from it's *revision*.

Each container holds at least one virtual environment folder that named by timestamp, which is a *revision*. With that convention, the latest version of environment can be sorted out and used without affecting existing container user.

```
~\.rezup                 # container root
   |
   + - {container}
   |     :
   :     :
   :     + - {revision}  # venv and bin tools lives here
   :     |
         + - {revision}  # folder named as timestamp, e.g. 1619780350.58
         |
         + - {revision}  # take latest when calling `rezup use {container}`


```

## Remote Container

To manage Rez venv in production, we may want every machine to have the same Rez venv setup and try keeping them up-to-date.

For this purpose, a centralized remote container is needed as a guidance for `rezup use` command to pick the right Rez venv setup from there, and create it locally if needed.

!!! question "How that works ?"

    When calling `rezup use {container}`, if the container has remote set, rezup will find the latest valid revision from remote and see if the same revision exists in local and use it. If not, create a new one by the recipe in that remote revision before use.

    But what if local container contains revisions that doesn't exists in remote ?

    The command `rezup use` always respect remote revision even there's more latest revision exists in local. Unless `rezup use --local` is used and remote will be ignored.

!!! info "The Difference"

    Both local and remote container have the same structure, the difference is the payload.
    
    === "Local"
        Where the Rez venv actually exists. Can be created by command
        ```
        rezup add {container}
        ```
    
    === "Remote"
        Only contains the venv installation manifest file (recipe) `rezup.toml` that uploaded by command
        ```
        rezup add {container} --remote
        ```

!!! tip "Local doesn't have to be in local"

    Local container root can be pointed into network drive, but if that's how it setup, keeps an eye on which Python interpreter is being used or the venv may not be usable.


## Recipe

A recipe file defines how a Rez venv should be built.

### File Naming

Recipe files usually be saved to and loaded from user home directory, and should be named with container (if not default container) so that command `rezup add <container>` could pick it up when creating corresponding container, for example:

* `~/rezup.toml` for container `.main`, the default
* `~/rezup.dev.toml` for container `dev`
* `~/rezup.test.toml` for container `test`
* `~/rezup.{name}.toml` for container `{name}`

### File Content

A recipe file may look like the following example, see below for details about each section.

```toml
description = "My rez setup"

[root]
local = false
remote = false

[dotenv]

[env]
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
name = "production"
requires = [
    "pyside2",
    "Qt5.py",
]

```


#### description

```toml
description = "hello, Rez!"
```

Like a comment, for knowing what this recipe is for.


#### root

Define where the root of this container should be.

```toml
[root]
local = ""
remote = "/studio/remote/.rezup"
```

=== "local"
    If the value is `false` or empty string `""`, env var `REZUP_ROOT_LOCAL` will be used, or the default `~/.rezup`.

=== "remote"
    If the value is `false` or empty string `""`, env var `REZUP_ROOT_REMOTE` will be used, or no remote for this container.


#### dotenv

The `.env` files will be loaded in order when container revision is being used, if provided.

```toml
[dotenv]
1 = "/to/my.env"    # non platform specific, load firstly, sort by key
2 = "/to/other.env"
[dotenv.linux]
a = "/to/lnx.env"   # platform specific, load secondly, sort by key
[dotenv.darwin]
a = "/to/mac.env"   # platform specific, load secondly, sort by key
[dotenv.windows]
a = "/to/win.env"   # platform specific, load secondly, sort by key
```

The key can be anything, they are only for sorting.


#### env

These will be loaded when container revision is being used, if provided.

```toml
[env]
REZ_CONFIG_FILE = "/path/to/rezconfig.py"
```


#### rez

Rez venv setup configurations

```toml
[rez]
# required
name = "rez"
url = "/path/to/source/rez"
# optional
edit = true
flags = ["-E"]
python = 3.7
```

|Name|Required|Description
| :---: | :---: | --- |
|name| O | The name of the package |
|url| O | The url that pass to `pip install`. Could be version specifier like `rez>=2.90`, or from version control like `git+https://github.com/nerdvegas/rez`, or local source path.|
|edit| - | Just like `pip install -e`, install package in edit mode or not. |
|python| - | The Python to create venv with. Use current if not set. Could be path to Python executable, or version |
|flags| - | Python interpreter flags, default `["-E"]` if not set. No flag will be added if the value is an empty list. |


#### extension

```toml
[[extension]]      # note this is a list but it's name is not plural
# required
name = "foo"
url = "foo>=0.5"
# optional
edit = false
flags = ["-E"]
isolation = true
python = 3.10      # ignored if `isolation` is false
```

Just like the section `rez`, but there's an extra option `isolation` can be used. Shouldn't be needed in most cases though.

If `isolation` is true, a venv will be created just for this extension with Rez installed as lib into it. If false as default, the extension will be installed into the Rez venv.


#### shared

```toml
[shared]
name = "production"
requires = [
    "pyside2",
    "Qt5.py",
]
```

For faster deploy, dependency packages can be installed in here, and will be shared across all revisions in one container (all revisions that use same `name` of shared lib).

This works by creating a `.pth` file that contains the absolute path of shared lib in Rez venv and only that venv. So this will not be shared with the extension that has `isolation` set to true.


## Production Install

Rezup installs Rez and the tooling by following Rez installation script's "production-install" schema :

1. Install Rez in a fresh Python virtual environment.
2. Command line entry-points (bin tools) are all patched with Python interpreter flag `-E`.
3. All bin tools get stored in a sub-directory of regular Python bin tools install location (`{venv}/bin/rez` or `{venv}/Scripts/rez` on Windows).

See Rez Wiki [Why Not Pip For Production?](https://github.com/nerdvegas/rez/wiki/Installation#why-not-pip-for-production) section for a bit more detail.

But if Rez gets installed in *edit-mode*, it will fail to compute the location of those production-installed bin tools and not able to provide features like nesting resolved contexts or running some specific rez tests.

Rezup covers this situation by using custom entry-point script. If Rez is going to be installed in edit-mode, all bin tools will be generated with the custom script, which will pre-cache the location of bin tools when the session starts if, the environment variable `REZUP_EDIT_IN_PRODUCTION` exists and is not empty (see [davidlatwe/rezup#56](https://github.com/davidlatwe/rezup/pull/56) for implementation detail).

You may put that env var in e.g. `rezup.dev.toml` like this:

```toml
[env]
REZUP_EDIT_IN_PRODUCTION = "1"

[rez]
name = "rez"
url = "/path/to/source/rez"
edit = true
```
