
import os
import sys
import stat
import logging
import tempfile
import shellingham

if sys.version_info.major == 2 and os.name == "nt":
    # patch missing `ctypes.wintypes` member in Py2 for `shellingham.nt`
    #   TODO: make a shellingham PR
    from ctypes import wintypes, c_char, POINTER
    wintypes.CHAR = c_char
    wintypes.PDWORD = POINTER(wintypes.DWORD)


# the script files are modified from virtualenv,
# not all shells been tested.
LAUNCH_SCRIPTS = {
    "up.bat": ["cmd"],
    "up.ps1": ["pwsh", "powershell"],
}


_log = logging.getLogger("rezup")


def get_current_shell():
    """Detect current shell with `shellingham`
    Note:
        On POSIX you might mostly get login shell instead of current shell.
        see rezup/launch/README#shell-detection
    """
    try:
        name, full_path = shellingham.detect_shell()
        return name, full_path
    except shellingham.ShellDetectionFailure:
        return provide_default(), None


def provide_default():
    if os.name == "posix":
        shell = os.environ["SHELL"]
    elif os.name == "nt":
        shell = os.environ["COMSPEC"]
    else:
        raise NotImplementedError("OS %r support not available" % os.name)

    shell, ext = os.path.splitext(os.path.basename(shell))
    shell = shell.lower()

    return shell


def get_launch_cmd(shell_name, shell_exec, interactive=False):
    """"""
    if shell_name == "cmd":
        command = [shell_exec]
        if interactive:
            command += ["/Q", "/K"]
        else:
            command += ["/Q", "/C"]

    elif shell_name in ("powershell", "pwsh"):
        command = [shell_exec, "-NoLogo", "-File"]
        if interactive:
            command.insert(1, "-NoExit")

    else:
        command = [shell_exec]
        if interactive:
            command.append("-i")

    # launch script for prompt, on Windows
    if shell_name in ("cmd", "powershell", "pwsh"):
        launch_script = generate_launch_script(
            shell_name,
            dst_dir=tempfile.mkdtemp(),
        )
        command.append(str(launch_script))

    _log.debug("Launch command:")
    _log.debug(" ".join(command))

    return command


def generate_launch_script(shell_name, dst_dir, replacement=None):
    replacement = replacement or dict()
    templates = os.path.dirname(__file__)

    for fname, supported_shells in LAUNCH_SCRIPTS.items():
        if shell_name not in supported_shells:
            continue

        template_script = os.path.join(templates, fname)
        if not os.path.isfile(template_script):
            continue

        # read as binary to avoid platform specific line norm (\n -> \r\n)
        with open(template_script, "rb") as f:
            binary = f.read()
        text = binary.decode("utf-8", errors="strict")

        for key, value in replacement.items():
            text = text.replace(key, value)

        launch_script = os.path.join(dst_dir, fname)
        with open(launch_script, "wb") as f:
            f.write(text.encode("utf-8"))

        st = os.stat(launch_script)
        os.chmod(launch_script, st.st_mode | stat.S_IEXEC)

        _log.debug("Launch script:\n\n" + text + "\n")

        return launch_script

    raise Exception(
        "Unsupported shell %r, cannot generate launch script." % shell_name
    )


def format_prompt_code(string, shell_name):
    codes = PROMPT_CODES.get(shell_name)
    if codes:
        return string.format(**codes)
    return string


_PROMPT_CODES_CMD = {
    "linebreak": "$_",
}
_PROMPT_CODES_PWSH = {
    "linebreak": "\n",
}
_PROMPT_CODES_CSH = {
    "linebreak": "\n",
}
_PROMPT_CODES_SH = {
    "linebreak": "\n",
}

PROMPT_CODES = {
    "cmd":        _PROMPT_CODES_CMD,
    "pwsh":       _PROMPT_CODES_PWSH,
    "powershell": _PROMPT_CODES_PWSH,
    "csh":        _PROMPT_CODES_CSH,
    "tcsh":       _PROMPT_CODES_CSH,
    "sh":         _PROMPT_CODES_SH,
    "zsh":        _PROMPT_CODES_SH,
    "bash":       _PROMPT_CODES_SH,
}


# ported from rez (modified from distlib)
def which(cmd, mode=os.F_OK | os.X_OK, env=None):
    """Given a command, mode, and a PATH string, return the path which
    conforms to the given mode on the PATH, or None if there is no such
    file.

    `mode` defaults to os.F_OK | os.X_OK. `env` defaults to os.environ,
    if not supplied.
    """
    # Check that a given file can be accessed with the correct mode.
    # Additionally check that `file` is not a directory, as on Windows
    # directories pass the os.access check.
    def _access_check(fn, mode_):
        return (os.path.exists(fn) and os.access(fn, mode_)
                and not os.path.isdir(fn))

    # Short circuit. If we're given a full path which matches the mode
    # and it exists, we're done here.
    if _access_check(cmd, mode):
        return cmd

    if env is None:
        env = os.environ

    path = env.get("PATH", os.defpath).split(os.pathsep)

    if sys.platform == "win32":
        # The current directory takes precedence on Windows.
        if os.curdir not in path:
            path.insert(0, os.curdir)

        # PATHEXT is necessary to check on Windows.
        default_pathext = \
            '.COM;.EXE;.BAT;.CMD;.VBS;.VBE;.JS;.JSE;.WSF;.WSH;.MSC'
        pathext = env.get("PATHEXT", default_pathext).split(os.pathsep)
        # See if the given file matches any of the expected path extensions.
        # This will allow us to short circuit when given "python.exe".
        matches = [cmd for ext in pathext if cmd.lower().endswith(ext.lower())]
        # If it does match, only test that one, otherwise we have to try
        # others.
        files = [cmd] if matches else [cmd + ext.lower() for ext in pathext]
    else:
        # On other platforms you don't have things like PATHEXT to tell you
        # what file suffixes are executable, so just pass on cmd as-is.
        files = [cmd]

    seen = set()
    for dir_ in path:
        dir_ = os.path.normcase(dir_)
        if dir_ not in seen:
            seen.add(dir_)
            for the_file in files:
                name = os.path.join(dir_, the_file)
                # On windows the system paths might have %systemroot%
                name = os.path.expandvars(name)
                if _access_check(name, mode):
                    return name
    return None
