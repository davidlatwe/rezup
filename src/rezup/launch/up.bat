@echo off
if "__REZUP_DO__" == "script" (
    call __REZUP_DO_SCRIPT__
    exit %errorlevel%
)
if "__REZUP_DO__" == "command" (
    __REZUP_DO_COMMAND__
    exit %errorlevel%
)

if not defined PROMPT (
    set "PROMPT=$P$G"
)
if defined REZUP_PROMPT (
    set "PROMPT=%REZUP_PROMPT%%PROMPT%"
)
