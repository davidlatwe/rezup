
import os
import stat
import shellingham
from pathlib import Path


# the script files are modified from virtualenv,
# not all shells been tested.
LAUNCH_SCRIPTS = {
    "up.bat": ["cmd"],
    "up.csh": ["csh", "tcsh"],
    "up.ps1": ["pwsh", "powershell"],
    "up.sh": ["sh", "bash", "zsh"],
}


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


def get_launch_cmd(shell_name, shell_exec, launch_script, block=True):
    if shell_name == "cmd":
        command = [shell_exec]
        if block:
            command += ["/Q", "/K"]
        else:
            command += ["/Q", "/C"]

    elif shell_name in {"powershell", "pwsh"}:
        command = [shell_exec, "-NoLogo", "-File"]
        if block:
            command.insert(1, "-NoExit")

    else:
        # TODO: use --rcs (zsh) or --rcfile (bash)
        command = [shell_exec]

    # if launch_script:
    #     launch_script = str(launch_script)
    #     command.append("--rcs")
    #     command.append(launch_script)

    return command


def generate_launch_script(name, dst_dir, replacements):
    template = Path(os.path.dirname(__file__))

    for fname, supported_shells in LAUNCH_SCRIPTS.items():
        if name not in supported_shells:
            continue
        # read as binary to avoid platform specific line norm (\n -> \r\n)
        with open(template / fname, "rb") as f:
            binary = f.read()
        text = binary.decode("utf-8", errors="strict")

        for key, value in replacements.items():
            if key == "__REZUP_PROMPT__":
                value = format_prompt_code(value, fname)
            text = text.replace(key, value)

        launch_script = dst_dir / fname
        with open(launch_script, "wb") as f:
            f.write(text.encode("utf-8"))

        st = os.stat(launch_script)
        os.chmod(launch_script, st.st_mode | stat.S_IEXEC)

        return launch_script

    print("Unsupported shell %r, no launch script generated." % name)


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
_PROMPT_CODES_SH = {
    "linebreak": "\n",
}

PROMPT_CODES = {
    "cmd": _PROMPT_CODES_CMD,
    "pwsh": _PROMPT_CODES_PWSH,
    "csh": _PROMPT_CODES_CSH,
    "sh": _PROMPT_CODES_SH,
}
