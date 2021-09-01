
import os
import shellingham
from pathlib import Path


# this shell name list is copied from shellingham,
# just for referencing.
SHELL_NAMES = (
    {"sh", "bash", "dash", "ash"}  # Bourne.
    | {"csh", "tcsh"}  # C.
    | {"ksh", "zsh", "fish"}  # Common alternatives.
    | {"cmd", "powershell", "pwsh"}  # Microsoft.
    | {"elvish", "xonsh"}  # More exotic.
)

# the script files are modified from virtualenv,
# not all shells been tested.
LAUNCH_SCRIPTS = {
    "up.bat": ["cmd"],
    "up.csh": ["csh", "tcsh"],
    "up.fish": ["fish"],
    "up.ps1": ["pwsh", "powershell"],
    "up.sh": ["sh", "bash", "zsh"],
    "up.xsh": ["xonsh"],
}


def get_current_shell():
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
        raise NotImplementedError(f"OS {os.name!r} support not available")

    shell, ext = os.path.splitext(os.path.basename(shell))
    shell = shell.lower()

    return shell


def get_launch_cmd(name, launch_dir, block=True):
    for script, supported_shells in LAUNCH_SCRIPTS.items():
        if name in supported_shells:
            launch_script = str(launch_dir / script)
            break
    else:
        raise Exception("No matching launch script for current shell: %s" % name)

    if name == "cmd":
        command = [name]
        if block:
            command += ["/Q", "/K"]
        else:
            command += ["/Q", "/C"]

    elif name in {"powershell", "pwsh"}:
        command = [name, "-NoLogo", "-File"]
        if block:
            command.insert(1, "-NoExit")

    else:
        command = [name]

    # Must have launch script
    command.append(launch_script)
    return command


def generate_launch_script(dst, replacements):
    location = Path(os.path.dirname(__file__))
    for fname in LAUNCH_SCRIPTS:
        # read content as binary to avoid platform specific line
        # normalization (\n -> \r\n)
        with open(location / fname, "rb") as f:
            binary = f.read()
        text = binary.decode("utf-8", errors="strict")
        for key, value in replacements.items():
            if key == "__REZUP_PROMPT__":
                value = format_prompt_code(value, fname)
            text = text.replace(key, value)

        with open(dst / fname, "wb") as f:
            f.write(text.encode("utf-8"))


def format_prompt_code(string, script_name):
    supported_shells = LAUNCH_SCRIPTS[script_name]
    shell = supported_shells[0]
    return string.format(**PROMPT_CODES[shell])


_PROMPT_CODES_CMD = {
    "linebreak": "$_",
}
_PROMPT_CODES_PWSH = {
    "linebreak": "\n",
}
_PROMPT_CODES_CSH = {
    "linebreak": "\n",
}
_PROMPT_CODES_FISH = {
    "linebreak": "\n",
}
_PROMPT_CODES_SH = {
    "linebreak": "\n",
}
_PROMPT_CODES_XONSH = {
    "linebreak": "\n",
}

PROMPT_CODES = {
    "cmd": _PROMPT_CODES_CMD,
    "pwsh": _PROMPT_CODES_PWSH,
    "csh": _PROMPT_CODES_CSH,
    "fish": _PROMPT_CODES_FISH,
    "sh": _PROMPT_CODES_SH,
    "xonsh": _PROMPT_CODES_XONSH,
}
