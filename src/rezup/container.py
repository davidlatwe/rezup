
import os
import sys
import json
import time
import shutil
import pkgutil
import tempfile
import subprocess
import virtualenv
from io import StringIO
from datetime import datetime
from dotenv import dotenv_values
from distlib.scripts import ScriptMaker

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

from ._vendor import toml
from .launch import shell


class ContainerError(Exception):
    pass


# TODO:
#   implement/document these env vars
#   - [x] REZUP_ROOT_REMOTE
#   - [x] REZUP_ROOT_LOCAL
#   - [ ] REZUP_CLEAN_AFTER


def makedirs(path):
    path = str(path)
    if not os.path.isdir(path):
        os.makedirs(path)


def rmtree(path):
    path = str(path)
    shutil.rmtree(path)


def iter_containers(root):
    root = str(root)
    if not (root and os.path.isdir(root)):
        return

    for dirname in os.listdir(root):
        yield Container(dirname, root=root)


class Container:
    """Timestamp ordered virtual environment stack

    A Rez venv provider, that allows updating venv continuously without
    affecting any existing consumer.

    In filesystem, a container is a folder that has at least one Rez venv
    installation exists, and those Rez venv folders (revisions) are named
    by timestamp, so when the container is being asked for a venv to use,
    the current latest available one will be sorted out.

    The location of the container can be set with env var `REZUP_ROOT_LOCAL`
    or `~/.rezup` will be used by default.

    For centralize management in production, one remote container can be
    defined with an env var `REZUP_ROOT_REMOTE`. The remote container only
    contains the venv installation manifest file, and when being asked, a
    venv will be created locally or re-used if same revision exists in local.

    """
    DEFAULT_NAME = ".main"
    BASE_RECIPE = (Path(__file__).parent / "rezup.toml").resolve()

    def __init__(self, name, root=None):
        root = Path(root) if root else self.default_root()

        self._remote = root == self.remote_root()
        self._name = name
        self._root = root
        self._path = root / name

    @classmethod
    def local_root(cls):
        default = os.path.expanduser("~/.rezup")
        from_env = os.getenv("REZUP_ROOT_LOCAL")
        return Path(from_env or default)

    @classmethod
    def remote_root(cls):
        from_env = os.getenv("REZUP_ROOT_REMOTE")
        return Path(from_env) if from_env else None

    @classmethod
    def default_root(cls):
        return cls.remote_root() or cls.local_root()

    @classmethod
    def create(cls, name, root=None):
        root = Path(root) if root else cls.default_root()
        makedirs(root / name)
        return Container(name, root)

    @classmethod
    def recipe_file(cls, name, ensure_exists=False):
        """Return container specific recipe file path

        The recipe file of default container '.main' will be '~/rezup.toml'

        And for other container, it will be `~/rezup.{name}.toml`
        for example:
            * `~/rezup.dev.toml`  -> container `dev`
            * `~/rezup.test.toml` -> container `test`

        Args:
            name(str): Container name
            ensure_exists(bool): If true, default recipe file will be
                generated if not exists. Default false.

        Returns:
            str: recipe file path

        """
        if name == cls.DEFAULT_NAME:
            file_path = os.path.expanduser("~/rezup.toml")
        else:
            file_path = os.path.expanduser("~/rezup.%s.toml" % name)

        if ensure_exists:
            with open(str(cls.BASE_RECIPE), "r") as r:
                with open(str(str(file_path)), "w") as w:
                    w.write(r.read())

        return Path(file_path)

    def root(self):
        """Root path of current container"""
        return self._root

    def name(self):
        """Name of current container"""
        return self._name

    def path(self):
        """Path of current container"""
        return self._path

    def libs(self):
        """Root path of current container's shared libraries"""
        return self._path / "libs"

    def revisions(self):
        """Root path of current container's revisions"""
        return self._path / "revisions"

    def is_exists(self):
        return self._path.is_dir()

    def is_empty(self):
        return not bool(next(self.iter_revision(), None))

    def is_remote(self):
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
        if not self.is_exists():
            return

        revisions_root = Revision.compose_path(container=self)
        if not revisions_root.is_dir():
            return

        revisions_root = str(revisions_root)
        for entry in sorted(os.listdir(revisions_root), reverse=latest_first):
            revision = Revision(container=self, dirname=entry)
            if not validate or revision.is_valid():
                yield revision

    def get_latest_revision(self, only_ready=True):
        for revision in self.iter_revision():
            if not only_ready or revision.is_ready():
                return revision

    def get_revision_at_time(self, timestamp, strict=False, only_ready=True):
        for revision in self.iter_revision():
            if not only_ready or revision.is_ready():
                if (revision.timestamp() == timestamp
                        or (not strict and revision.timestamp() <= timestamp)):
                    return revision

    def new_revision(self, recipe_file):
        return Revision.create(self, recipe_file)


class Revision:

    def __init__(self, container, dirname=None):
        dirname = str(dirname or time.time())

        self._container = container
        self._dirname = dirname
        self._path = self.compose_path(container, dirname)
        self._timestamp = None
        self._is_valid = None
        self._recipe = self._path / "rezup.toml"  # revision internal recipe
        self._metadata = self._path / "revision.json"

    @classmethod
    def compose_path(cls, container, dirname=None):
        path = container.revisions()
        if dirname:
            path /= dirname
        return path

    @classmethod
    def create(cls, container, recipe_file):
        recipe_file = Path(recipe_file)
        revision = cls(container=container)
        revision._write(recipe_file)
        return revision

    def _write(self, recipe_file, pulling=False):
        if not recipe_file.is_file():
            raise Exception("Recipe file not exists: %s" % recipe_file)

        if not pulling:
            print("Recipe sourced from: %s" % recipe_file)

        if not self._path.is_dir():
            makedirs(self._path)

        with open(str(self._metadata), "w") as f:
            # metadata
            f.write(json.dumps({
                # "creator":
                # "hostname":
                "revision_path": str(self._path),
            }, indent=4))

        if not self.is_valid():
            raise Exception("Invalid new revision, this is a bug.")

        _con_name = self._container.name()

        # compose recipe
        #
        recipe = toml.load(str(Container.BASE_RECIPE))
        deep_update(recipe, toml.load(str(recipe_file)))

        # install
        #
        if not self._container.is_remote():
            self._install(recipe)

        # cleanup entries that revision doesn't need
        #
        recipe.pop("init", None)

        # save recipe, mark as ready
        #
        with open(str(self._recipe), "w") as f:
            toml.dump(recipe, f)

    def _install(self, recipe):
        """Construct Rez virtual environment by recipe

        Example recipe file `rezup.toml`

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

        """
        tools = [Tool(data) for data in recipe.get("extension", [])]
        shared = recipe.get("shared")

        installer = Installer(self)
        installer.install_rez(Tool(recipe["rez"]))
        if shared:
            installer.create_shared_lib(name=shared["name"],
                                        requires=shared["requires"])
        for tool in tools:
            installer.install_extension(tool)

    def validate(self):
        is_valid = True
        seconds = float(self._dirname)
        timestamp = datetime.fromtimestamp(seconds)
        if self._metadata.is_file():
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
        return self._recipe.is_file()

    def is_remote(self):
        return self._container.is_remote()

    def dirname(self):
        return self._dirname

    def path(self):
        return self._path

    def timestamp(self):
        return self._timestamp

    def container(self):
        return self._container

    def recipe(self):
        if self.is_ready():
            return toml.load(str(self._recipe))

    def recipe_env(self):
        recipe_env = (self.recipe() or {}).get("env")
        if not recipe_env:
            return

        buffer = StringIO()
        parsed_recipe_env = ConfigParser(recipe_env)
        parsed_recipe_env.write(buffer)

        buffer.seek(0)  # must reset buffer
        recipe_env_dict = dotenv_values(buffer)  # noqa

        return {
            k: v for k, v in recipe_env_dict.items()
            if v is not None  # exclude config section line
        }

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

    def pull(self):
        if not self.is_remote():
            raise Exception("Cannot pull revision from local container.")

        # get local
        _con_name = self._container.name()
        local = Container.create(_con_name, root=Container.local_root())
        revision = local.get_revision_at_time(self._timestamp, strict=True)
        if revision is None:
            print("Pulling from remote container %s .." % _con_name)
            revision = Revision(container=local, dirname=self._dirname)
            revision._write(self._recipe, pulling=True)

        return revision

    def use(self, run_script=None):
        if not self.is_valid():
            raise Exception("Cannot use invalid revision.")
        if not self.is_ready():
            raise Exception("Revision is not ready to be used.")

        if self.is_remote():
            # use local
            revision = self.pull()
            return revision.use(run_script=run_script)

        else:
            # Launch subprocess
            replacement = dict()
            environment = self._compose_env()
            shell_name, shell_exec = self._get_shell()

            if run_script and os.path.isfile(run_script):
                # run shell script and exit
                block = False
                replacement["__REZUP_DO__"] = "script"
                replacement["__REZUP_DO_SCRIPT__"] = os.path.abspath(run_script)

            elif run_script:
                # run shell command and exit
                block = False
                replacement["__REZUP_DO__"] = "command"
                replacement["__REZUP_DO_COMMAND__"] = run_script

            else:
                # interactive shell
                block = True
                replacement["__REZUP_SHELL__"] = shell_exec
                prompt = "rezup (%s) " % self._container.name()
                prompt = shell.format_prompt_code(prompt, shell_name)
                environment.update({
                    "REZUP_PROMPT": os.getenv("REZUP_PROMPT", prompt),
                })

            launch_script = shell.generate_launch_script(
                shell_name,
                dst_dir=tempfile.mkdtemp(),
                replacement=replacement
            )
            cmd = shell.get_launch_cmd(shell_name,
                                       shell_exec,
                                       launch_script,
                                       block=block)

            popen = subprocess.Popen(cmd, env=environment)
            stdout, stderr = popen.communicate()

            return popen.returncode

    def _compose_env(self):
        env = os.environ.copy()
        env.update(self.recipe_env() or {})
        env.update({
            "REZUP_CONTAINER": self._container.name(),
        })

        env["PATH"] = os.pathsep.join([
            str(self._path / "bin"),
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

    def locate_rez_lib(self, venv_session=None):
        """Try finding Rez module location"""
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

    def get_rez_version(self, venv_session=None):
        rez_location = self.locate_rez_lib(venv_session)
        version_py = rez_location / "rez" / "utils" / "_version.py"
        if version_py.is_file():
            _locals = {"_rez_version": ""}
            with open(str(version_py)) as f:
                exec(f.read(), globals(), _locals)
            return _locals["_rez_version"]


class Tool:

    def __init__(self, data):
        self.name = data["name"]
        self.url = data.get("url", data["name"])
        self.edit = data.get("edit", False)
        self.isolation = data.get("isolation", False)
        self.python = data.get("python", None)


class Installer:

    def __init__(self, revision):
        self._container = revision.container()
        self._revision = revision
        self._default_venv = None
        self._rez_as_libs = None
        self._rez_version = None

    def installed_rez_version(self):
        return self._rez_version

    def install_rez(self, tool):
        assert tool.name == "rez"

        venv_session = self.create_venv(tool)
        self._default_venv = venv_session
        self._rez_as_libs = tool

        self.install_package(tool, venv_session)

    def install_extension(self, tool):
        if tool.isolation:
            venv_session = self.create_venv(tool)
        else:
            venv_session = self._default_venv

        if venv_session is None:
            raise Exception("No python venv created, this is a bug.")

        if venv_session is not self._default_venv:
            self.install_package(self._rez_as_libs, venv_session, make_scripts=False)
        self.install_package(tool, venv_session)

    def create_venv(self, tool):
        use_python = tool.python or sys.executable
        dst = self._revision.path() / "venv" / tool.name

        # create venv
        args = [
            "--python", str(use_python),
            str(dst)
        ]
        session = virtualenv.cli_run(args)

        return session

    def install_package(self, tool, venv_session, make_scripts=True):
        python_exec = str(venv_session.creator.exe)
        cmd = [python_exec, "-m", "pip", "install"]

        if tool.edit:
            cmd += ["--editable", tool.url]
        else:
            cmd.append(tool.url)

        cmd += [
            # don't make noise
            "--disable-pip-version-check",
        ]

        print("Installing %s.." % tool.name)
        subprocess.check_output(cmd)

        if make_scripts:
            self.create_production_scripts(tool, venv_session)
            if tool.name == "rez":
                self.mark_as_rez_production_install(venv_session)

    def mark_as_rez_production_install(self, venv_session):
        validator = self._revision.path() / "bin" / ".rez_production_install"
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
        site_packages = venv_session.creator.purelib

        if tool.edit:
            egg_link = site_packages / ("%s.egg-link" % tool.name)
            with open(str(egg_link), "r") as f:
                package_location = f.readline().strip()
            path = [str(package_location)]
        else:
            path = [str(site_packages)]

        dists = Distribution.discover(name=tool.name, path=path)
        specifications = [
            "{ep.name} = {ep.value}".format(ep=ep)
            for dist in dists
            for ep in dist.entry_points
            if ep.group == "console_scripts"
        ]

        bin_path = self._revision.path() / "bin"
        if not bin_path.is_dir():
            makedirs(bin_path)

        maker = ScriptMaker(source_dir=None, target_dir=str(bin_path))
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

        scripts = maker.make_multiple(
            specifications=specifications,
            options=dict(interpreter_args=["-E"])
        )

        return scripts

    def create_shared_lib(self, name, requires):
        lib_path = str(self._container.libs() / name)

        venv_session = self._default_venv
        python_exec = str(venv_session.creator.exe)
        cmd = [python_exec, "-m", "pip", "install", "-U"]

        cmd += requires
        cmd += [
            # don't make noise
            "--disable-pip-version-check",
            "--target",
            lib_path,
        ]

        subprocess.check_output(cmd)

        # link shared lib with rez venv (the default venv)
        site_packages = venv_session.creator.purelib
        with open(str(site_packages / "_shared.pth"), "w") as f:
            f.write(lib_path)


def deep_update(dict1, dict2):
    for key, value in dict2.items():
        if isinstance(dict1.get(key), dict) and isinstance(value, dict):
            deep_update(dict1[key], value)
        else:
            dict1[key] = value
