
import os
import sys
import stat
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
    "up.csh": ["csh", "tcsh"],
    "up.ps1": ["pwsh", "powershell"],
    "up.sh":  ["sh", "bash", "zsh"],
}


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


def get_launch_cmd(shell_name, shell_exec, launch_script, block=True):
    """"""
    if shell_name == "cmd":
        command = [shell_exec]
        if block:
            command += ["/Q", "/K"]
        else:
            command += ["/Q", "/C"]

    elif shell_name in ("powershell", "pwsh"):
        command = [shell_exec, "-NoLogo", "-File"]
        if block:
            command.insert(1, "-NoExit")

    else:
        command = [shell_exec]

    command.append(str(launch_script))

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
