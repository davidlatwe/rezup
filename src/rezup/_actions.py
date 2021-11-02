"""This script runs by rez-python in Rez venv, DO NOT import as module.

This script may be executed by different version of Python, so better to watch
out if the .pyc file exists and is being called ($ python _actions.pyc) or
expect "bad magic number in .pyc file" error.

Should be safe as long as this script has not been imported (been compiled) and
most importantly, not being called as "_actions.pyc". Still, to be more safe,
better add "-B" flag to the interpreter before calling this script.

"""
import os
import sys
import json

global message_wrap


def _flush(message):
    message = message_wrap % message
    sys.stdout.write(message)
    sys.stdout.flush()


def action_resolve(requests_or_rxt):
    from rez.resolved_context import ResolvedContext  # noqa

    if os.path.isfile(requests_or_rxt):
        context = ResolvedContext.load(requests_or_rxt)
    else:
        context = ResolvedContext(requests_or_rxt.split(" "))

    resolved_env = context.get_environ()
    resolved_env_str = json.dumps(resolved_env)
    _flush(resolved_env_str)


if __name__ == "__main__":
    message_wrap, action_name = sys.argv[1:3]

    action_func = sys.modules[__name__].__dict__.get(action_name)
    if action_func is None:
        raise Exception("Action not found: %s" % action_name)

    argv = sys.argv[3:]
    action_func(*argv)
