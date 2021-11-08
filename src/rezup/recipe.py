
import re
import sys
from copy import deepcopy
from contextlib import contextmanager

try:
    from pathlib import Path  # noqa, py3
except ImportError:
    from pathlib2 import Path  # noqa, py2

if sys.version_info.major == 2:
    from UserDict import DictMixin  # noqa, py2
else:
    from collections.abc import MutableMapping as DictMixin

from ._vendor import toml


DEFAULT_CONTAINER_NAME = ".main"  #: default container name: `.main`
DEFAULT_CONTAINER_RECIPES = Path.home()  #: user home directory


class BaseRecipe(DictMixin, object):
    """Dict-like baseclass of recipe object"""
    DEFAULT_RECIPE = (Path(__file__).parent / "rezup.toml").resolve()

    def __init__(self, name):
        self._name = name or DEFAULT_CONTAINER_NAME
        self._file = None
        self._path = None
        self.__data = None

    @property
    def _data(self):
        if self.__data is None:
            self._load()
        return self.__data

    def _load(self):
        data = toml.load(str(self.DEFAULT_RECIPE))
        path = self.path()
        if path.is_file():
            deep_update(data, toml.load(str(path)))
        self.__data = data

    def __repr__(self):
        return "%s(name=%s, path=%s)" % (
            self.__class__.__name__, self.name(), self.path())

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):
        for key in self._data.keys():
            yield key

    def __len__(self):
        return len(self._data)

    def keys(self):
        return self._data.keys()

    def path(self):
        """Returns the path of this recipe, implement in subclass"""
        raise NotImplementedError

    def create(self):
        """Write out recipe content, implement in subclass"""
        raise NotImplementedError

    def name(self):
        """Returns the container name of this recipe corresponding to"""
        return self._name

    def data(self):
        """Returns a copy of parsed recipe file content"""
        return deepcopy(self._data)

    def is_file(self):
        """Returns True if recipe file exists, False otherwise."""
        return self.path().is_file()


class ContainerRecipe(BaseRecipe):
    """A dict-like representation of container's recipe

    The recipe file of default container '.main' will be '~/rezup.toml'

    And for other container, it will be `~/rezup.{name}.toml`
    for example:
        * `~/rezup.dev.toml`  -> container `dev`
        * `~/rezup.test.toml` -> container `test`

    Args:
        name (str, optional): Container name

    """
    REGEX = re.compile("rezup.?(.*).toml")
    RECIPES_DIR = DEFAULT_CONTAINER_RECIPES  #: `DEFAULT_CONTAINER_RECIPES`

    def __init__(self, name=None):
        super(ContainerRecipe, self).__init__(name)
        _name = self._name
        if _name and _name != DEFAULT_CONTAINER_NAME:
            self._file = "rezup.%s.toml" % _name
        else:
            self._file = "rezup.toml"

    @classmethod
    @contextmanager
    def provisional_recipes(cls, path):
        """Context for changing recipes root temporarily

        Container recipes should be in user's home directory by defaule, but
        that could be changed inside this context for the case when you need
        to operate on machines that have no recipe exists in home directory.

        ```
        with ContainerRecipe.provisional_recipes("/to/other/recipes"):
            ...
        ```

        Args:
            path (str or path-like): directory path where recipes located
        """
        default = cls.RECIPES_DIR
        try:
            cls.RECIPES_DIR = Path(path)
            yield
        finally:
            cls.RECIPES_DIR = default

    @classmethod
    def iter_recipes(cls):
        """Iter all recipe files found in `ContainerRecipe.RECIPES_DIR`
        Yields:
            `ContainerRecipe`
        """
        for item in cls.RECIPES_DIR.iterdir():
            if not item.is_file():
                continue
            match = cls.REGEX.search(item.name)
            if match:
                name = match.group(1)
                yield cls(name)

    def path(self):
        """Returns the file path of this recipe
        Returns:
            pathlib.Path: The file path of this recipe
        """
        if self._path is None:
            self._path = self.RECIPES_DIR / self._file
        return self._path

    def create(self, data=None):
        """Write out recipe content into a .toml file
        Args:
            data (dict, optional): Arbitrary data to write out
        """
        if not self.RECIPES_DIR.is_dir():
            self.RECIPES_DIR.mkdir(parents=True)
        path = self.path()

        if data:
            _data = toml.load(str(self.DEFAULT_RECIPE))
            deep_update(_data, data)
            with open(str(path), "w") as f:
                toml.dump(_data, f)
        else:
            # read & write as plaintext, so the comment can be preserved
            with open(str(self.DEFAULT_RECIPE), "r") as r:
                with open(str(path), "w") as w:
                    w.write(r.read())
        self._load()


class RevisionRecipe(BaseRecipe):
    """A dict-like representation of revision's internal recipe
    Args:
        revision (Revision): A rezup revision instance
    """
    def __init__(self, revision):
        name = revision.container().name()
        super(RevisionRecipe, self).__init__(name)
        self._file = "rezup.toml"
        self._revision = revision

    def path(self):
        """Returns the file path of this recipe
        Returns:
            pathlib.Path
        """
        if self._path is None:
            self._path = self._revision.path() / self._file
        return self._path

    def create(self):
        """Write revision recipe from it's container"""
        path = self.path()
        container_recipe = self._revision.container().recipe()
        with open(str(path), "w") as f:
            toml.dump(container_recipe.data(), f)
        self._load()

    def pull(self, revision):
        """Write revision recipe from other revision"""
        path = self.path()
        revision_recipe = revision.recipe()
        with open(str(path), "w") as f:
            toml.dump(revision_recipe.data(), f)
        self._load()


def deep_update(dict1, dict2):
    for key, value in dict2.items():
        if isinstance(dict1.get(key), dict) and isinstance(value, dict):
            deep_update(dict1[key], value)
        else:
            dict1[key] = value
