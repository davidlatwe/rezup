
import os
import sys
import json
import time
import shutil
import socket
import getpass
import pkgutil
import logging
import platform
import functools
import subprocess
import virtualenv
from datetime import datetime
from dotenv import dotenv_values
from distlib.scripts import ScriptMaker

try:
    from dotenv.compat import StringIO  # py2
except ImportError:
    from io import StringIO  # py3

try:
    from pathlib import Path  # noqa, py3
except ImportError:
    from pathlib2 import Path  # noqa, py2

try:
    from configparser import ConfigParser  # noqa, py3
except ImportError:
    from ConfigParser import ConfigParser  # noqa, py2

try:
    from importlib.metadata import Distribution  # noqa
except ImportError:
    from importlib_metadata import Distribution

from . import __version__
from .launch import shell
from .recipe import ContainerRecipe, RevisionRecipe, DEFAULT_CONTAINER_NAME
from .exceptions import ContainerError


_PY2 = sys.version_info.major == 2
_log = logging.getLogger("rezup")


# TODO:
#   implement/document these env vars
#   - [x] REZUP_ROOT_REMOTE
#   - [x] REZUP_ROOT_LOCAL
#   - [ ] REZUP_CLEAN_AFTER


if _PY2:
    string_types = basestring,  # noqa
else:
    string_types = str,


def makedirs(path):
    path = str(path)
    if not os.path.isdir(path):
        os.makedirs(path)


def rmtree(path):
    path = str(path)
    shutil.rmtree(path)


def norm_path(path):
    return os.path.expanduser(path)


def iter_containers():
    """Iterate containers by recipes (`~/rezup[.{name}].toml`)

    Returns:
        Generator[rezup.Container]: Instance of [rezup.Container][], could be
            linked to remote or local.

    """
    for recipe in ContainerRecipe.iter_recipes():
        name = recipe.name()
        container = Container(name, recipe)
        yield container  # could be remote
        if get_container_root(recipe, remote=False) != container.root():
            # previous container is remote, now yield local
            yield Container(name, recipe, force_local=True)


def get_container_root(recipe, remote=False):
    """Get container root path from recipe

    ```toml
    # rezup.foo.toml
    [root]
    local = false
    remote = "/path/to/remote/containers"

    ```

    If the `recipe` represents the above example recipe file, container named
    `foo` will have local root set to `rezup.recipe.DEFAULT_CONTAINER_RECIPES`,
    unless environ variable `REZUP_ROOT_LOCAL` has value. And the remote root
    will set to `/path/to/remote/containers`.

    Args:
        recipe (`ContainerRecipe`): The container recipe to lookup from.
        remote (bool): Fetch remote root if True, otherwise local.

    Returns:
        `pathlib.Path`: Container root path, local or remote one.

    """
    data = recipe.data()
    if remote:
        remote = \
            data["root"]["remote"] \
            or os.getenv("REZUP_ROOT_REMOTE")

        return Path(norm_path(remote)) if remote else None

    else:
        local = \
            data["root"]["local"] \
            or os.getenv("REZUP_ROOT_LOCAL") \
            or "~/.rezup"

        return Path(norm_path(local))


class Container:
    """Timestamp ordered virtual environment stack

    A Rez venv provider, that allows updating venv continuously without
    affecting any existing consumer.

    In filesystem, a container is a folder that has at least one Rez venv
    installation exists, and those Rez venv folders (`Revision`) are named
    by timestamp, so when the container is being asked for a venv to use,
    the current latest available one will be sorted out.

    The location of the container can be set with env var `REZUP_ROOT_LOCAL`
    or `~/.rezup` will be used by default.

    For centralize management in production, one remote container can be
    defined with an env var `REZUP_ROOT_REMOTE`. The remote container only
    contains the venv installation manifest file, and when being asked, a
    venv will be created locally or re-used if same revision exists in local.

    Args:
        name (`str`, optional): Container name, use `Container.DEFAULT_NAME`
            if not given.
        recipe (`ContainerRecipe`, optional): A `ContainerRecipe` object to
            help constructing container, will look into `ContainerRecipe.RECIPES_DIR`
            if not given.
        force_local (`bool`, optional): Default `False`. Ignore linking remote
            even if the remote path has set, always link to local if `True`.

    """
    DEFAULT_NAME = DEFAULT_CONTAINER_NAME  #: `rezup.recipe.DEFAULT_CONTAINER_NAME`

    def __init__(self, name=None, recipe=None, force_local=False):
        name = name or self.DEFAULT_NAME
        recipe = recipe or ContainerRecipe(name)

        local_root = get_container_root(recipe, remote=False)
        remote_root = get_container_root(recipe, remote=True)
        if force_local:
            root = local_root
        else:
            root = remote_root or local_root

        self._remote = root == remote_root
        self._recipe = recipe
        self._name = name
        self._root = root
        self._path = root / name

    def __repr__(self):
        return "%s(remote=%d, name=%r, path=%r)" % (
            self.__class__.__name__,
            int(self.is_remote()),
            self.name(),
            self._path.resolve(),
        )

    @classmethod
    def create(cls, name, force_local=False):
        """Create container from recipe.

        Args:
            name (str): The name of container.
            force_local (bool): Create as local if True, or try remote.

        Returns:
            `Container`: A container instance.
        """
        recipe = ContainerRecipe(name)
        _log.debug("Sourcing recipe from: %s" % recipe)
        if not recipe.is_file():
            _log.debug("Recipe file not exists, creating default..")
            recipe.create()
        return Container(name, recipe, force_local)

    def root(self):
        """
        Returns:
            `pathlib.Path`: Path to where this container is located.
        """
        return self._root

    def name(self):
        """
        Returns:
            str: Container name.
        """
        return self._name

    def path(self):
        """
        Returns:
            `pathlib.Path`: Full path of this container.
        """
        return self._path

    def recipe(self):
        """
        Returns:
            `ContainerRecipe`: The recipe instance that binds to this container.
        """
        return self._recipe

    def libs(self):
        """
        Returns:
            `pathlib.Path`: Path to this container's shared libraries.
        """
        return self._path / "libs"

    def revisions(self):
        """
        Returns:
            `pathlib.Path`: Path to this container's revisions.
        """
        return self._path / "revisions"

    def is_exists(self):
        """
        Returns:
            bool: Return `True` if this container exists.
        """
        return self._path.is_dir()

    def is_empty(self):
        """
        Returns:
            bool: Return `True` if this container has no valid revisions.
        """
        return not bool(next(self.iter_revision(), None))

    def is_remote(self):
        """
        Returns:
            bool: Return `True` if this container is linked to remote side.
        """
        return self._remote

    def purge(self):
        if self.is_exists():
            revision = self.get_latest_revision(only_ready=False)
            if not revision:
                # TODO: don't remove it immediately, mark as purged and
                #   remove it when $REZUP_CLEAN_AFTER meet
                rmtree(self._path)
            else:
                # TODO: should have better exception type
                # TODO: need to check revision is in use
                raise Exception("Revision is creating.")

        # keep tidy, try remove the root of containers if it's now empty
        root = self.root()
        if root.is_dir() and not next(root.iterdir(), None):
            rmtree(root)

    def iter_revision(self, validate=True, latest_first=True):
        """Iterating revisions from this container.

        Args:
            validate (bool, optional): Default `True`. Only yield revisions
                that are valid if `True`.
            latest_first (bool): Default `True`. Yield revisions based on
                it's directory name (timestamp string) in descending order,
                or ascending if `False`.

        Yields:
            Revision: `Revision` instances that match the condition.

        """
        _log.debug("Iterating revisions in container %s.." % self)

        if not self.is_exists():
            _log.debug("Container %r not exists." % self.name())
            return

        revisions_root = Revision.compose_path(container=self)
        if not revisions_root.is_dir():
            _log.debug("Revision root is not a directory: %s" % revisions_root)
            return

        revisions_root = str(revisions_root)
        for entry in sorted(os.listdir(revisions_root), reverse=latest_first):
            revision = Revision(container=self, dirname=entry)
            _log.debug("... %s" % revision)
            if not validate or revision.is_valid():
                yield revision

    def get_latest_revision(self, only_ready=True):
        """Get latest revision from this container.

        Args:
            only_ready (bool): Default `True`. Include revisions that are not
                in ready state if `False`.

        Returns:
            Revision: An instance of `Revision` if found, or `None`.

        """
        for revision in self.iter_revision():
            if not only_ready or revision.is_ready():
                _log.debug("Found latest revision.")
                return revision

    def get_revision_by_time(self, timestamp, fallback=False, only_ready=True):
        """Returns a revision that match the timestamp

        Args:
            timestamp (datetime.datetime): a time for matching revision
            fallback (bool): If True, accept earlier revision when no exact matched
            only_ready (bool): Include revisions that are not in ready state if False

        Returns:
            Revision: An instance of `Revision` if found, or `None`.

        """
        for revision in self.iter_revision():
            if not only_ready or revision.is_ready():
                if (revision.timestamp() == timestamp
                        or (fallback and revision.timestamp() <= timestamp)):

                    _log.debug("Found time matched revision.")
                    return revision

        _log.debug("No time matched revision found.")

    def new_revision(self):
        """Create a new revision

        Returns:
            Revision: An instance of `Revision` that just created.

        """
        return Revision.create(self)


class Revision:
    """
    Args:
        container (Container): The container that holds this revision
        dirname (str, optional): Directory name of this revision, should be
            a timestamp string if given.
    """

    def __init__(self, container, dirname=None):
        dirname = str(dirname or time.time())

        self._container = container
        self._dirname = dirname
        self._path = self.compose_path(container, dirname)
        self._timestamp = None
        self._is_valid = None
        self._metadata = None
        self._recipe = RevisionRecipe(self)
        self._metadata_path = self._path / "revision.json"
        self._is_pulled = False

    def __repr__(self):
        return "%s(valid=%d, ready=%d, remote=%d, time=%s, path=%r)" % (
            self.__class__.__name__,
            int(self.is_valid()),
            int(self.is_ready()),
            int(self.is_remote()),
            self.time_str() or "?",
            self._path.resolve(),
        )

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self._container.name() == other._container.name() \
            and self.timestamp() == other.timestamp()

    @classmethod
    def compose_path(cls, container, dirname=None):
        path = container.revisions()
        if dirname:
            path /= dirname
        return path

    @classmethod
    def create(cls, container):
        revision = cls(container=container)
        revision._write()
        return revision

    def _write(self, pulling=None):
        """Sourcing recipe and create a revision

        Args:
            pulling (Revision, optional): If given, pulling recipe from that
                revision, usually a remote one.
        """
        _log.info("Creating revision..")

        recipe = self._recipe
        makedirs(self._path)

        # write revision recipe
        if pulling is None:
            _log.info("Recipe sourced from: %s" % self._container.recipe())
            recipe.create()
        else:
            _log.debug("Pulling recipe from: %s" % pulling)
            recipe.pull(pulling)

        if not self.is_valid():
            raise Exception("Invalid new revision, this is a bug.")

        # manifest
        rez_ = Tool(recipe["rez"])
        extensions = [Tool(d) for d in recipe.get("extension", []) if d]
        shared_lib = recipe.get("shared")
        _log.info("Recipe loaded.")
        _log.debug("       Rez: %s" % rez_.url)
        _log.debug(" Extension: " + ", ".join([e.name for e in extensions]))
        _log.debug("Shared-lib: %s" % shared_lib)

        # install, if at local
        if not self._container.is_remote():
            self._install(rez_, extensions, shared_lib)

        # save metadata, mark revision as ready
        with open(str(self._metadata_path), "w") as f:
            # metadata
            f.write(json.dumps({
                "rezup_version": __version__,
                "creator": getpass.getuser(),
                "hostname": socket.gethostname(),
                "revision_path": str(self._path),
                "venvs": ["rez"] + [t.name for t in extensions if t.isolation],
            }, indent=4))

        _log.info("Revision created: %s" % self)

    def _install(self, rez_, extensions=None, shared_lib=None):
        """Construct Rez virtual environment by recipe
        """
        _log.debug("Installing..")

        pip_entry = self._recipe.get("pip")
        extensions = extensions or []
        installer = Installer(
            self,
            pip_opt=pip_entry.get("options"),
            pip_env=pip_entry.get("env"),
        )

        installer.install_rez(rez_)

        if shared_lib:
            installer.create_shared_lib(name=shared_lib["name"],
                                        requires=shared_lib["requires"])
        for ext in extensions:
            installer.install_extension(ext)

    def validate(self):
        is_valid = True
        seconds = float(self._dirname)
        timestamp = datetime.fromtimestamp(seconds)
        if self._recipe.is_file():
            self._timestamp = timestamp
        else:
            is_valid = False

        return is_valid

    def is_valid(self):
        if self._is_valid is None:
            try:
                self._is_valid = self.validate()
            except (OSError, ValueError):
                self._is_valid = False

        return self._is_valid

    def is_ready(self):
        return self._metadata_path.is_file()

    def is_remote(self):
        return self._container.is_remote()

    def dirname(self):
        return self._dirname

    def path(self):
        return self._path

    def timestamp(self):
        return self._timestamp

    def time_str(self):
        return self._timestamp.strftime("%d.%b.%y %H:%M") \
            if self._timestamp else ""

    def container(self):
        return self._container

    def metadata(self):
        if self.is_ready():
            if self._metadata is None:
                with open(str(self._metadata_path), "r") as f:
                    self._metadata = json.load(f)
            return self._metadata

    def recipe(self):
        if self.is_valid():
            return self._recipe

    def recipe_env(self):
        _platform = platform.system().lower()
        recipe = self.recipe() or {}
        env = {}

        def load_env(**kwargs):
            return {
                k: v for k, v in dotenv_values(**kwargs).items()
                if v is not None  # exclude config section line
            }

        def file_loader(d):
            return [d[k] for k in sorted([
                k for k, v in d.items() if isinstance(v, string_types)])]

        dot_env = recipe.get("dotenv")
        if dot_env:
            # non platform specific dotenv
            env_files = file_loader(dot_env)
            if isinstance(dot_env.get(_platform), dict):
                # platform specific dotenv
                env_files += file_loader(dot_env[_platform])

            for file in env_files:
                env.update(load_env(dotenv_path=file))

        recipe_env = recipe.get("env")
        if recipe_env:
            stream = StringIO()

            _parser = ConfigParser()
            _parser.optionxform = str  # to prevent turning keys into lowercase
            _parser.read_dict({"env": recipe_env})
            _parser.write(stream)

            stream.seek(0)  # must reset buffer
            env.update(load_env(stream=stream))

        env.update({
            "REZUP_CONTAINER": self._container.name(),
            "REZUP_USING_REMOTE": "yes" if self._is_pulled else "",
        })

        return env

    def purge(self):
        if self.is_valid():
            # TODO: don't remove it immediately, mark as purged and
            #   remove it when $REZUP_CLEAN_AFTER meet
            rmtree(self._path)

    def iter_backward(self):
        for revision in self._container.iter_revision(latest_first=True):
            if revision.timestamp() < self._timestamp:
                yield revision

    def iter_forward(self):
        for revision in self._container.iter_revision(latest_first=False):
            if revision.timestamp() > self._timestamp:
                yield revision

    def pull(self, check_out=True, fallback=False):
        """Return corresponding local side revision

        If the revision is from remote container, calling this method will
        find a timestamp matched local revision and create one if not found
        by default.

        If the revision is from local container, return `self`.

        Args:
            check_out (bool, optional): When no matched local revision,
                create one if True or just return None at the end.
                Default is True.
            fallback (bool, optional)

        Returns:
            Revision or None

        """
        if not self.is_remote():
            return self

        # get local
        _con_name = self._container.name()
        _con_recipe = self._container.recipe()  # careful, this affect's root

        local = Container(_con_name, recipe=_con_recipe, force_local=True)
        rev = local.get_revision_by_time(self._timestamp,
                                         fallback=fallback,
                                         only_ready=True)

        _allow_create = rev is None and check_out
        _did_fallback = rev.timestamp() != self._timestamp if rev else False

        if not fallback and _allow_create:
            _log.info("Pulling from remote container: %s" % self._container)
            rev = Revision(container=local, dirname=self._dirname)
            rev._write(pulling=self)

        if fallback and _did_fallback:
            _log.warning(
                "Local revision at exact time (%s) is not ready, "
                "fallback to %s" % (self.time_str(), rev)
            )

        if rev is not None:
            rev._is_pulled = True

        return rev

    def spawn_shell(self, command=None):
        """Spawn a sub-shell

        Args:
            command (list, optional): Shell script file with args or commands.
                If given, the sub-shell will not be interactive.

        Returns:
            subprocess.Popen

        Raises:
            ContainerError

        """
        if not self.is_valid():
            raise ContainerError("Cannot use invalid revision.")
        if not self.is_ready():
            raise ContainerError("Revision is not ready to be used.")

        if self.is_remote():
            # use local
            revision = self.pull()
            if revision is None:
                raise ContainerError("No revision pulled.")
            if not revision.is_ready():
                raise ContainerError("Revision is not ready to be used.")

            return revision.spawn_shell(command=command)

        else:
            # Launch subprocess
            environment = self._compose_env()
            shell_name, shell_exec = self._get_shell()

            if command:
                # run command and exit
                if command[0] == ".":
                    cmd = command
                else:
                    exe = command[0]
                    exe = shell.which(exe, env=environment) or exe
                    cmd = [exe] + command[1:]

            else:
                # interactive shell
                _con_name = self._container.name()
                _con_from = "remote" if self._is_pulled else "local"
                prompt = "rezup (%s/%s) " % (_con_name, _con_from)
                prompt = shell.format_prompt_code(prompt, shell_name)
                environment.update({
                    "REZUP_PROMPT": os.getenv("REZUP_PROMPT", prompt),
                })

                cmd = shell.get_launch_cmd(
                    shell_name,
                    shell_exec,
                    interactive=True,
                )

            popen = subprocess.Popen(cmd, env=environment)

            return popen

    def use(self, command=None, wait=True):
        """Run a sub-shell

        Args:
            command (list, optional): Shell script with args or commands. If
                given, the sub-shell will not be interactive.
            wait (bool, optional): Whether to wait `command` finish or not,
                default True.

        Returns:
            int: subprocess return code, will always return 0 if `command`
                is given and `wait` is False.

        """
        block = not command
        popen = self.spawn_shell(command=command)

        if block or wait:
            stdout, stderr = popen.communicate()
            return popen.returncode
        else:
            return 0

    def _compose_env(self):
        env = os.environ.copy()
        env.update(self.recipe_env() or {})
        env["PATH"] = os.pathsep.join([
            os.pathsep.join([str(p) for p in self.production_bin_dirs()]),
            env["PATH"]
        ])
        # use `pythonfinder` package if need to exclude python from PATH

        return env

    def _get_shell(self):
        shell_name = os.getenv("REZUP_DEFAULT_SHELL")
        if shell_name:
            shell_exec = shell_name
            shell_name, ext = os.path.splitext(os.path.basename(shell_name))
            shell_name = shell_name.lower()
        else:
            shell_name, shell_exec = shell.get_current_shell()
            shell_exec = shell_exec or shell_name

        return shell_name, shell_exec

    def _require_local(method):  # noqa
        """Decorator for ensuring local revision exists before action
        """
        @functools.wraps(method)  # noqa
        def wrapper(self, *args, **kwargs):
            if not self.is_remote():
                return method(self, *args, **kwargs)  # noqa

            check_out = bool(os.getenv("REZUP_ALWAYS_CHECKOUT"))
            revision = self.pull(check_out=check_out)
            if revision is None:
                raise ContainerError(
                    "This revision is from remote container, no matched found "
                    "in local. Possible not been pulled into local yet."
                )

            return getattr(revision, method.__name__)(self, *args, **kwargs)

        return wrapper

    @_require_local  # noqa
    def locate_rez_lib(self, venv_session=None):
        """Returns rez module location in this revision

        Returns:
            pathlib.Path or None if not found.

        """
        if venv_session is None:
            venv_path = self.path() / "venv" / "rez"
            venv_session = virtualenv.session_via_cli(args=[str(venv_path)])
        venv_lib = venv_session.creator.purelib

        # rez may get installed in edit mode, try short route first
        egg_link = venv_lib / "rez.egg-link"
        if egg_link.is_file():
            with open(str(egg_link), "r") as f:
                package_location = f.readline().strip()
            if os.path.isdir(package_location):
                return Path(package_location)

        for importer, modname, pkg in pkgutil.walk_packages([str(venv_lib)]):
            if pkg and modname == "rez":
                loader = importer.find_module(modname)
                try:
                    path = loader.path  # SourceFileLoader
                    return Path(path).parent.parent
                except AttributeError:
                    path = loader.filename  # ImpLoader, py2
                    return Path(path).parent

    @_require_local  # noqa
    def get_rez_version(self, venv_session=None):
        """Returns rez version installed in this revision

        Returns:
            str or None if not found.

        """
        rez_location = self.locate_rez_lib(venv_session)
        if rez_location is None:
            return

        version_py = rez_location / "rez" / "utils" / "_version.py"
        if version_py.is_file():
            _locals = {"_rez_version": ""}
            with open(str(version_py)) as f:
                exec(f.read(), globals(), _locals)
            return _locals["_rez_version"]

    @_require_local  # noqa
    def production_bin_dir(self, venv_name):
        """Returns production bin scripts dir in this revision

        Returns:
            pathlib.Path, but the directory may not exists.

        """
        bin_dirname = "Scripts" if platform.system() == "Windows" else "bin"
        venv_bin_dir = self.path() / "venv" / venv_name / bin_dirname
        return venv_bin_dir / "rez"

    @_require_local  # noqa
    def production_bin_dirs(self):
        bin_dirs = []

        metadata = self.metadata()
        if metadata and not metadata.get("rezup_version"):
            # rezup-1.x
            _log.debug("Is a 'rezup-1.x' styled revision.")
            bin_dirs.append(self._path / "bin")
        else:
            # rezup-2.x
            _log.debug("Is a 'rezup-2.x' styled revision.")
            for venv_name in metadata.get("venvs", []):
                bin_dirs.append(self.production_bin_dir(venv_name))

        return bin_dirs


class Tool:

    def __init__(self, data):
        self.name = data["name"]
        self.url = data.get("url", data["name"])
        self.edit = data.get("edit", False)
        self.isolation = data.get("isolation", False)
        self.python = data.get("python", None)
        self.flags = data.get("flags", ["-E"])

    def __repr__(self):
        return "%s(name=%s, edit=%d, url=%s, isolation=%d, python=%s)" % (
            self.__class__.__name__,
            self.name,
            int(self.edit),
            self.url,
            int(self.isolation),
            self.python,
        )


class Installer:

    def __init__(self, revision, pip_opt=None, pip_env=None):
        self._container = revision.container()
        self._revision = revision
        self._pip_opt = pip_opt or []
        self._pip_env = pip_env or dict()
        self._default_venv = None
        self._rez_as_libs = None
        self._rez_version = None
        self._rez_in_edit = None

    def installed_rez_version(self):
        return self._rez_version

    def install_rez(self, tool):
        assert tool.name == "rez"

        venv_session = self.create_venv(tool)
        self._default_venv = venv_session
        self._rez_as_libs = tool
        self._rez_in_edit = tool.edit

        self.install_package(tool, venv_session, patch_scripts=True)

    def install_extension(self, tool):
        if tool.isolation:
            venv_session = self.create_venv(tool)
        else:
            venv_session = self._default_venv

        if venv_session is None:
            raise Exception("No python venv created, this is a bug.")

        if venv_session is not self._default_venv:
            self.install_package(self._rez_as_libs, venv_session)
        self.install_package(tool, venv_session, patch_scripts=True)

    def create_venv(self, tool):
        use_python = tool.python or sys.executable
        dst = self._revision.path() / "venv" / tool.name

        _log.info("Creating virtual env..")
        _log.info("  Python: %s" % use_python)
        _log.info("       -> %s" % dst)

        # create venv
        args = [
            "--python", str(use_python),
            str(dst)
        ]
        session = virtualenv.cli_run(args)

        return session

    def install_package(self, tool, venv_session, patch_scripts=False):
        python_exec = str(venv_session.creator.exe)
        cmd = [python_exec, "-m", "pip", "install"]

        if tool.edit:
            cmd += ["--editable", tool.url]
        else:
            cmd.append(tool.url)

        cmd += self._pip_opt

        env = os.environ.copy()
        env.update(self._pip_env)

        _log.info("Installing %s.." % tool)
        _log.debug("  full command: %s" % " ".join(cmd))
        subprocess.check_output(cmd, env=env)

        if patch_scripts:
            self.create_production_scripts(tool, venv_session)
            if tool.name == "rez":
                self.mark_as_rez_production_install(tool, venv_session)
                # TODO: copy completion scripts

    def mark_as_rez_production_install(self, tool, venv_session):
        _log.info("Mark as Rez production install..")

        rez_bin = self._revision.production_bin_dir("rez")
        validator = rez_bin / ".rez_production_install"
        rez_version = self._revision.get_rez_version(venv_session)
        assert rez_version is not None, "Rez version not obtain."

        with open(str(validator), "w") as f:
            f.write(rez_version)
        self._rez_version = rez_version

    def create_production_scripts(self, tool, venv_session):
        """Create Rez production used binary scripts

        The binary script will be executed with Python interpreter flag -E,
        which will ignore all PYTHON* env vars, e.g. PYTHONPATH and PYTHONHOME.

        """
        _log.info("Generating production scripts..")

        site_packages = venv_session.creator.purelib
        bin_path = venv_session.creator.bin_dir

        if tool.edit:
            egg_link = site_packages / ("%s.egg-link" % tool.name)
            if not egg_link.is_file():
                _log.error("Tool %r installed in edit mode, but unable "
                           "to find egg-link for generating production "
                           "scripts from source. File not exists: %s" %
                           (tool.name, egg_link))
                return

            with open(str(egg_link), "r") as f:
                package_location = f.readline().strip()
            path = [str(package_location)]
        else:
            path = [str(site_packages)]

        dists = Distribution.discover(name=tool.name, path=path)
        specifications = {
            ep.name: "{ep.name} = {ep.value}".format(ep=ep)
            for dist in dists
            for ep in dist.entry_points
            if ep.group == "console_scripts"
        }

        # delete bin files written into virtualenv
        # this also avoided naming conflict between script 'rez' and dir 'rez'
        for script_name in specifications.keys():
            script_path = bin_path / script_name
            if script_path.is_file():
                os.remove(str(script_path))

        venv_name = tool.name if tool.isolation else "rez"
        prod_bin_path = self._revision.production_bin_dir(venv_name)
        makedirs(prod_bin_path)

        maker = ScriptMaker(source_dir=None, target_dir=str(prod_bin_path))
        maker.executable = str(venv_session.creator.exe)

        # Align with wheel
        #
        # Ensure we don't generate any variants for scripts because this is
        # almost never what somebody wants.
        # See https://bitbucket.org/pypa/distlib/issue/35/
        maker.variants = {""}
        # Ensure old scripts are overwritten.
        # See https://github.com/pypa/pip/issues/1800
        maker.clobber = True
        # This is required because otherwise distlib creates scripts that are
        # not executable.
        # See https://bitbucket.org/pypa/distlib/issue/32/
        maker.set_mode = True

        if self._rez_in_edit:
            # Allow pre-caching rez_bin_path on script entry if environ var
            # `REZUP_EDIT_IN_PRODUCTION` is set with non-empty value.
            # See https://github.com/davidlatwe/rezup/pull/56
            maker.script_template = r'''# -*- coding: utf-8 -*-
import re
import os
import sys
from %(module)s import %(import_name)s
if os.getenv("REZUP_EDIT_IN_PRODUCTION"):
    from rez.system import system
    setattr(system, 'rez_bin_path', r'{rez_bin_path}')
if __name__ == '__main__':
    sys.argv[0] = re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])
    sys.exit(%(func)s())
'''.format(rez_bin_path=str(prod_bin_path))

        scripts = maker.make_multiple(
            specifications=specifications.values(),
            options=dict(interpreter_args=list(tool.flags))
        )

        return scripts

    def create_shared_lib(self, name, requires):
        _log.info("Installing shared libs..")

        lib_path = str(self._container.libs() / name)

        venv_session = self._default_venv
        python_exec = str(venv_session.creator.exe)
        cmd = [python_exec, "-m", "pip", "install", "-U"]

        cmd += requires
        cmd += self._pip_opt
        cmd += [
            "--target",
            lib_path,
        ]

        env = os.environ.copy()
        env.update(self._pip_env)

        _log.debug("  full command: %s" % " ".join(cmd))
        subprocess.check_output(cmd, env=env)

        # link shared lib with rez venv (the default venv)
        site_packages = venv_session.creator.purelib
        with open(str(site_packages / "_rezup_shared.pth"), "w") as f:
            f.write(lib_path)
