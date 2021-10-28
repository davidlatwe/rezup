
import os
import re
import sys
import json
import subprocess


def locate_rez_lib(container=None, create=False):
    """Return Rez lib location form container if found

    Args:
        container (str, optional): container name, use default container
            if name not given.
        create (bool, optional): create local revision if not exists,
            default False.

    Returns:
        (pathlib.Path): rez lib location if found

    Raises:
        ContainerError: when no valid revision to use

    """
    revision = _get_revision(container, create=create)
    return revision.locate_rez_lib()


def resolve_environ(requests_or_rxt, container=None, create=False):
    """Resolve package requests with Rez from container

    This will try to locate Rez lib from container, insert into sys.path,
    and import rez to do the resolve.

    Args:
        requests_or_rxt: List of strings or list of PackageRequest objects,
            or, a resolved context RXT file.
        container (str, optional): Container name, use default container
            if name not given.
        create (bool, optional): Create local revision if not exists,
            default False.

    Returns:
        dict: The environment dict generated by the resolved context.

    Raises:
        ContainerError: when no valid revision to use.

    """
    from . import ContainerError

    revision = _get_revision(container, create=create)
    env = os.environ.copy()
    env.update(revision.recipe_env() or {})

    ext = ".exe" if sys.platform == "win32" else ""
    rez_python = None

    for bin_dir in revision.production_bin_dirs():
        _exec = str(bin_dir / ("rez-python" + ext))
        if os.access(_exec, os.X_OK):
            rez_python = _exec
            break

    if rez_python is None:
        raise ContainerError("rez-python not found in revision: %s"
                             % revision.path())

    if isinstance(requests_or_rxt, list):
        requests_or_rxt = " ".join(requests_or_rxt)

    args = [
        rez_python,
        __file__,
        _run_resolve.__action_name__,
        requests_or_rxt
    ]
    popen = subprocess.Popen(
        args,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    out, err = popen.communicate()
    polished_out = polish(out)
    if polished_out:
        return json.loads(polished_out)


def _get_revision(container=None, create=False):
    from . import Container, ContainerError

    name = container or Container.DEFAULT_NAME
    container = Container(name)

    revision = container.get_latest_revision()

    if revision is None:
        if container.is_remote():
            raise ContainerError("No valid revision in container %r: %s"
                                 % (container.name(), container.path()))
        elif create:
            revision = container.new_revision()

    revision = revision.pull(check_out=create)
    if revision is None:
        raise ContainerError("No matched revision in local container.")

    return revision


# actions
# notes: maybe the actions could be loaded from entry-points.

_message_wrap = "::rezup.msg.start::%s::rezup.msg.end::"
_polish_regex = re.compile(_message_wrap % "(.*)")


def action(name):
    def decorator(fn):
        setattr(fn, "__action_name__", name)
        return fn
    return decorator


def get_action(name):
    for attr, obj in sys.modules[__name__].__dict__.items():
        if name == getattr(obj, "__action_name__", None):
            return obj


def polish(message):
    match = _polish_regex.search(message)
    if match:
        return match.group(1)


def flush(message):
    message = _message_wrap % message
    sys.stdout.write(message)
    sys.stdout.flush()


@action("resolve")
def _run_resolve(requests_or_rxt):
    from rez.resolved_context import ResolvedContext  # noqa

    if os.path.isfile(requests_or_rxt):
        context = ResolvedContext.load(requests_or_rxt)
    else:
        context = ResolvedContext(requests_or_rxt.split(" "))

    resolved_env = context.get_environ()
    resolved_env_str = json.dumps(resolved_env)
    flush(resolved_env_str)


if __name__ == "__main__":
    action_name = sys.argv[:2][-1]
    action_func = get_action(action_name)
    if action_func is None:
        raise Exception("Action not found: %s" % action_name)

    argv = sys.argv[2:]
    action_func(*argv)
