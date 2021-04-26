
import os
import sys
import json
import shutil
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
from .launch import shell


class ContainerError(Exception):
    pass


# TODO:
#   implement/document these env vars
#   - REZUP_ROOT_REMOTE
#   - REZUP_ROOT_LOCAL
#   - REZUP_IGNORE_REMOTE
#   - REZUP_CLEAN_AFTER


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
                # TODO: don't remove it immediately, mark as purged and
                #   remove it when $REZUP_CLEAN_AFTER meet
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
        """
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
        tools = []
        installer = Installer(self)

        tools.append(Tool(recipe["rez"]))
        for data in recipe.get("extension", []):
            tools.append(Tool(data))

        for tool in tools:
            installer.install(tool)

        # make launch scripts, for prompt and job run
        _con_name = self._container.name()
        _rez_ver = installer.installed_rez_version() or "unknown"
        _revision_date = self._timestamp.strftime("%m/%d/%Y, %H:%M:%S")
        _prompt_info = (_con_name, _rez_ver, _revision_date)
        prompt_string = "(%s) - Rez %s - %s{linebreak}" % _prompt_info

        replacements = {
            "__REZUP_PROMPT__": prompt_string,
        }
        shell.generate_launch_script(self._path, replacements)

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
            # TODO: don't remove it immediately, mark as purged and
            #   remove it when $REZUP_CLEAN_AFTER meet
            shutil.rmtree(self._path)

    def iter_backward(self):
        for revision in self._container.iter_revision(latest_first=True):
            if revision.timestamp() < self._timestamp:
                yield revision

    def iter_forward(self):
        for revision in self._container.iter_revision(latest_first=False):
            if revision.timestamp() > self._timestamp:
                yield revision

    def use(self, run_script=None):
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

            if run_script:
                env["__REZUP_SCRIPT__"] = os.path.abspath(run_script)
                block = False
            else:
                block = True

            shell_name, _ = shell.get_current_shell()
            cmd = shell.get_launch_cmd(shell_name, self._path, block=block)

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

    def __init__(self, revision):
        self._container = revision.container()
        self._revision = revision
        self._default_venv = None
        self._shared_tools = list()
        self._rez_version = None

    def installed_rez_version(self):
        return self._rez_version

    def install(self, tool):
        if tool.isolation or tool.name == "rez":
            venv_session = self.create_venv(tool)
            if tool.name == "rez":
                self._default_venv = venv_session
                self._shared_tools.append(tool)
        else:
            venv_session = self._default_venv

        if venv_session is None:
            raise Exception("No python venv created, this is a bug.")

        if venv_session is not self._default_venv:
            for shared in self._shared_tools:
                self.install_package(shared, venv_session)

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

    def install_package(self, tool, venv_session):
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

        self.create_production_scripts(tool, venv_session)
        if tool.name == "rez":
            self.mark_as_rez_production_install(tool, venv_session)

    def mark_as_rez_production_install(self, tool, venv_session):
        validator = self._revision.path() / "bin" / ".rez_production_install"
        version_py = (
            Path(tool.url) / "src" if tool.edit
            else venv_session.creator.purelib  # site-packages
        ) / "rez" / "utils" / "_version.py"

        _locals = {"_rez_version": ""}
        with open(version_py) as f:
            exec(f.read(), globals(), _locals)
        with open(validator, "w") as f:
            f.write(_locals["_rez_version"])

        self._rez_version = _locals["_rez_version"]

    def create_production_scripts(self,
                                  tool,
                                  venv_session):
        """Create Rez production used binary scripts

        The binary script will be executed with Python interpreter flag -E,
        which will ignore all PYTHON* env vars, e.g. PYTHONPATH and PYTHONHOME.

        """
        site_packages = venv_session.creator.purelib

        if tool.edit:
            egg_link = site_packages / ("%s.egg-link" % tool.name)
            with open(egg_link, "r") as f:
                package_location = f.readline().strip()
            path = [str(package_location)]
        else:
            path = [str(site_packages)]

        dists = Distribution.discover(name=tool.name, path=path)
        specifications = [
            f"{ep.name} = {ep.value}"
            for dist in dists
            for ep in dist.entry_points
            if ep.group == "console_scripts"
        ]

        bin_path = self._revision.path() / "bin"
        if not bin_path.is_dir():
            os.makedirs(bin_path)

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
