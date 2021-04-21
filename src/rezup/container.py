"""
{container}/
    |
    +-- {timestamp}/
    |   |   <revision>
    :   |
        +-- venv/
        |   |
        |   +-- _rez/
        |   |   <default rez venv>
        |   |
        |   +-- {extension}/
        |   |   <venv for extension that require isolation>
        |   :
        |
        +-- rez, rezgui, rezplugins, .egg-info/
        |   <rez package install, shared with all venvs>
        |
        +-- bin/
        |   <all bin tools>
        |
        >-- rezup.toml
        |   <recipe file>
        |
        >-- revision.json
            <info of this container revision>

"""
import os
import sys
import json
import shutil
import pkgutil
import subprocess
import virtualenv
from distlib.scripts import ScriptMaker
from pathlib import Path
from datetime import datetime

try:
    from importlib.metadata import Distribution
except ImportError:
    from importlib_metadata import Distribution

from ._vendor import toml
from .shell import get_current_shell, get_launch_cmd


class ContainerError(Exception):
    pass


# REZUP_ROOT_REMOTE
# REZUP_ROOT_LOCAL
# REZUP_IGNORE_REMOTE
# REZUP_CONTAINER_PATH
# REZUP_CONTAINER_REZ_PATH


class Container:

    def __init__(self, name, root=None, is_remote=False):
        root = Path(root) if root else self.default_root()

        self._remote = is_remote
        self._name = name
        self._root = root
        self._path = root / name

    @classmethod
    def default_root(cls, is_remote=False):
        if is_remote:
            if "REZUP_ROOT_REMOTE" not in os.environ:
                raise Exception("Remote root not not provided.")
            else:
                return Path(os.environ["REZUP_ROOT_REMOTE"])
        else:
            return Path(
                os.getenv("REZUP_ROOT_LOCAL", os.path.expanduser("~/.rezup"))
            )

    @classmethod
    def create(cls, name, root=None, is_remote=False):
        root = Path(root) if root else cls.default_root(is_remote)
        os.makedirs(root / name, exist_ok=True)
        return Container(name, root, is_remote)

    def root(self):
        return self._root

    def name(self):
        return self._name

    def path(self):
        return self._path

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
                shutil.rmtree(self._path)
            else:
                # TODO: should have better exception type
                # TODO: need to check revision is in use
                raise Exception("Revision is creating.")

        # keep tidy, try remove the root of containers if it's now empty
        root = self.root()
        if os.path.isdir(root) and not os.listdir(root):
            shutil.rmtree(root)

    def iter_revision(self, validate=True, latest_first=True):
        if not self.is_exists():
            return
        for entry in sorted(os.listdir(self._path), reverse=latest_first):
            if not os.path.isdir(self._path / entry):
                continue

            revision = Revision(entry, container=self)
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

    def new_revision(self, recipe_file=None, timestamp=None):
        return Revision.create(self, recipe_file, timestamp)


class Revision:

    def __init__(self, dirname, container):
        self._container = container
        self._dirname = dirname
        self._path = container.path() / dirname
        self._timestamp = None
        self._is_valid = None
        self._recipe = self._path / "rezup.toml"

    @classmethod
    def create(cls, container, recipe_file=None, timestamp=None):
        dir_name = str(timestamp or datetime.now().timestamp())
        revision_path = container.path() / dir_name
        revision_file = revision_path / "revision.json"

        os.makedirs(revision_path, exist_ok=True)
        with open(revision_file, "w") as f:
            # metadata
            f.write(json.dumps({
                # "creator":
                # "hostname":
                "revision_path": str(revision_path),
            }, indent=4))

        revision = cls(dir_name, container=container)
        if not revision.is_valid():
            raise Exception("Invalid new revision, this is a bug.")

        # compose recipe
        recipe = toml.load(Path(os.path.dirname(__file__)) / "rezup.toml")
        user_recipe_file = os.path.expanduser("~/rezup.toml")
        if not recipe_file and os.path.isfile(user_recipe_file):
            recipe_file = user_recipe_file
        if recipe_file:
            deep_update(recipe, toml.load(recipe_file))
        # install
        if not container.is_remote():
            revision._install(recipe)
        # mark as ready
        with open(revision._recipe, "w") as f:
            toml.dump(recipe, f)

        return revision

    def _install(self, recipe):
        tools = []
        installer = Installer(self)

        tools.append(Tool(recipe["rez"]))
        for data in recipe.get("extensions", []):
            tools.append(Tool(data))

        for tool in tools:
            installer.install(tool)

        # TODO: make activators, for prompt and script run

    def validate(self):
        is_valid = True
        seconds = float(self._dirname)
        timestamp = datetime.fromtimestamp(seconds)
        if os.path.isfile(self._path / "revision.json"):
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
        return os.path.isfile(self._recipe)

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
            return toml.load(self._recipe)

    def purge(self):
        if self.is_valid():
            shutil.rmtree(self._path)

    def iter_backward(self):
        for revision in self._container.iter_revision(latest_first=True):
            if revision.timestamp() < self._timestamp:
                yield revision

    def iter_forward(self):
        for revision in self._container.iter_revision(latest_first=False):
            if revision.timestamp() > self._timestamp:
                yield revision

    def use(self):
        if not self.is_valid():
            raise Exception("Cannot use invalid revision.")
        if not self.is_ready():
            raise Exception("Revision is not ready to be used.")

        if self._container.is_remote():
            # get local
            name = self._container.name()
            container = Container.create(name, is_remote=False)
            revision = container.get_revision_at_time(self._timestamp,
                                                      strict=True)
            if revision is None:
                revision = container.new_revision(self._recipe, self._timestamp)
            # use local
            return revision.use()

        else:
            # Launch subprocess
            env = os.environ.copy()
            env["PATH"] = os.pathsep.join([
                str(self._path / "bin"),
                env["PATH"]
            ])
            # use `pythonfinder` package if need to exclude python from PATH

            shell_name, _ = get_current_shell()
            cmd = get_launch_cmd(shell_name)

            popen = subprocess.Popen(cmd, env=env)
            stdout, stderr = popen.communicate()

            return popen.returncode


class Tool:

    def __init__(self, data):
        self.name = data["name"]
        self.url = data["url"]
        self.edit = data.get("edit", False)
        self.isolation = data.get("isolation", False)
        self.python = data.get("python", None)


class Installer:

    site_template = r"""# -*- coding: utf-8 -*-
import site
site.addsitedir(r"{revision}")
"""

    def __init__(self, revision):
        self._container = revision.container()
        self._revision = revision
        self._default_venv = None

    def install(self, tool):
        if tool.isolation or tool.name == "rez":
            venv_session = self.create_venv(tool)
            if tool.name == "rez":
                self._default_venv = venv_session
        else:
            venv_session = self._default_venv

        if venv_session is None:
            raise Exception("No python venv created, this is a bug.")

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

        # add sitecustomize.py
        site_script = session.creator.purelib / "sitecustomize.py"
        sitecustomize = self.site_template.format(revision=self._revision.path())
        with open(site_script, "w") as f:
            f.write(sitecustomize)

        return session

    def install_package(self, tool, venv_session):
        python_exec = str(venv_session.creator.exe)
        cmd = [python_exec, "-m", "pip", "install"]

        if tool.edit:
            cmd.append("-e")
        cmd.append(tool.url)

        # don't make noise
        cmd.append("--disable-pip-version-check")

        if tool.name == "rez":
            cmd += ["--target", str(self._revision.path())]

        print("Installing %s.." % tool.name)
        subprocess.check_output(cmd)

        if tool.name == "rez":
            self.rez_production_install(tool, venv_session)
        else:
            self.create_production_scripts(tool, venv_session)

    def rez_production_install(self, tool, venv_session):
        bin_path = self._revision.path() / "bin"
        rez_cli = self._revision.path() / "rez" / "cli"
        version_py = self._revision.path() / "rez" / "utils" / "_version.py"

        rez_entries = None
        for importer, modname, _ in pkgutil.iter_modules([str(rez_cli)]):
            if modname == "_entry_points":
                loader = importer.find_module(modname)
                rez_entries = loader.load_module(modname)
                break

        for file in os.listdir(bin_path):
            os.remove(bin_path / file)
        specifications = rez_entries.get_specifications().values()
        self.create_production_scripts(tool, venv_session, specifications)

        # mark as production install
        _locals = {"_rez_version": ""}
        with open(version_py) as f:
            exec(f.read(), globals(), _locals)
        with open(bin_path / ".rez_production_install", "w") as f:
            f.write(_locals["_rez_version"])

    def create_production_scripts(self,
                                  tool,
                                  venv_session,
                                  specifications=None):
        """Create Rez production used binary scripts

        The binary script will be executed with Python interpreter flag -E,
        which will ignore all PYTHON* env vars, e.g. PYTHONPATH and PYTHONHOME.

        """
        if specifications is None:
            site_packages = str(venv_session.creator.purelib)
            dists = Distribution.discover(name=tool.name, path=[site_packages])
            specifications = [
                f"{ep.name} = {ep.value}"
                for dist in dists
                for ep in dist.entry_points
                if ep.group == "console_scripts"
            ]

        bin_path = self._revision.path() / "bin"

        maker = ScriptMaker(source_dir=None, target_dir=bin_path)
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


def deep_update(dict1, dict2):
    for key, value in dict2.items():
        if isinstance(dict1.get(key), dict) and isinstance(value, dict):
            deep_update(dict1[key], value)
        else:
            dict1[key] = value
