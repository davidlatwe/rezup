
import re
import sys
from copy import deepcopy

try:
    from pathlib import Path  # noqa, py3
except ImportError:
    from pathlib2 import Path  # noqa, py2

if sys.version_info.major == 2:
    from UserDict import DictMixin  # noqa, py2
else:
    from collections.abc import MutableMapping as DictMixin

from ._vendor import toml


DEFAULT_CONTAINER_NAME = ".main"


class BaseRecipe(DictMixin, object):
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
        raise NotImplementedError

    def create(self):
        raise NotImplementedError

    def name(self):
        return self._name

    def data(self):
        return deepcopy(self._data)

    def is_file(self):
        return self.path().is_file()


class ContainerRecipe(BaseRecipe):
    """Container's recipe

    The recipe file of default container '.main' will be '~/rezup.toml'

    And for other container, it will be `~/rezup.{name}.toml`
    for example:
        * `~/rezup.dev.toml`  -> container `dev`
        * `~/rezup.test.toml` -> container `test`

    Args:
        name(str): Container name

    """
    REGEX = re.compile("rezup.?(.*).toml")
    RECIPES_DIR = Path.home()

    def __init__(self, name=None):
        super(ContainerRecipe, self).__init__(name)
        _name = self._name
        if _name and _name != DEFAULT_CONTAINER_NAME:
            self._file = "rezup.%s.toml" % _name
        else:
            self._file = "rezup.toml"

    @classmethod
    def iter_recipes(cls):
        for item in cls.RECIPES_DIR.iterdir():
            if not item.is_file():
                continue
            match = cls.REGEX.search(item.name)
            if match:
                name = match.group(1)
                yield cls(name)

    def path(self):
        if self._path is None:
            self._path = self.RECIPES_DIR / self._file
        return self._path

    def create(self, data=None):
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
    """Revision's internal recipe
    """
    def __init__(self, revision):
        name = revision.container().name()
        super(RevisionRecipe, self).__init__(name)
        self._file = "rezup.toml"
        self._revision = revision

    def path(self):
        if self._path is None:
            self._path = self._revision.path() / self._file
        return self._path

    def create(self):
        path = self.path()
        container_recipe = self._revision.container().recipe()
        with open(str(path), "w") as f:
            toml.dump(container_recipe.data(), f)
        self._load()


def deep_update(dict1, dict2):
    for key, value in dict2.items():
        if isinstance(dict1.get(key), dict) and isinstance(value, dict):
            deep_update(dict1[key], value)
        else:
            dict1[key] = value
