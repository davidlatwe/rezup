
import os
import shellingham


def get_current_shell():
    try:
        name, full_path = shellingham.detect_shell()
        return name, full_path
    except shellingham.ShellDetectionFailure:
        return provide_default(), None


def provide_default():
    if os.name == "posix":
        return os.environ["SHELL"]
    elif os.name == "nt":
        return os.environ["COMSPEC"]
    raise NotImplementedError(f"OS {os.name!r} support not available")


def get_launch_cmd(name, block=True, script=None):
    if name == "cmd":
        return [name, "/Q", "/K"]

    elif name in {"powershell", "pwsh"}:
        return [name, "-NoExit", "-NoLogo"]  # "-File"

    else:
        return [name]
