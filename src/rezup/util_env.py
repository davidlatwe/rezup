"""Container environ one-line injector

Example:
    ```python
    from rezup.util_env import dot_main
    # the environ of container '.main' has been applied onto `os.environ`
    ...
    # import other stuff
    ```
With this module, we could inject container environ at the top of script with
import statement in one line, instead of something like this:

```python
from rezup.util import get_revision
os.environ.update(get_revision(".main").recipe_env())
...
# import other stuff
```

Which makes linter unhappy.


!!! important "However, Python 3.7+ Required"
    The feature this module provides is based on
    [PEP-562](https://www.python.org/dev/peps/pep-0562/), which requires
    **Python 3.7+** to work.

"""
import os
import sys
from . import util
from .container import iter_containers

if sys.version_info < (3, 7):
    raise ImportError("This container environ injector needs Python 3.7+ "
                      "(PEP-562).")


def __dir__():
    """Listing all container as valid importable attribute name

    Example:
        >>> from rezup import util_env
        >>> dir(util_env)
        ['dev', 'dot_main']

    """
    return [
        "dot_main" if name == ".main" else name
        for name in [con.name() for con in iter_containers()]
    ]


def __getattr__(name):
    """Returns a dict of environ that given from specified container

    Example:
        >>> from rezup import util_env
        >>> util_env.dot_main  # the env also been applied onto os.environ
        {'REZUP_CONTAINER': '.main', 'REZUP_USING_REMOTE': ''}

    """
    if name[:2] == name[-2:] == "__":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    if name == "dot_main":
        con_name = ".main"
    else:
        con_name = name

    revision = util.get_revision(container=con_name)
    env = revision.recipe_env()
    os.environ.update(env)

    return env
