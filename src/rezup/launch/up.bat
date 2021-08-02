@echo off

if not defined PROMPT (
    set "PROMPT=$P$G"
)
if not defined REZUP_DISABLE_PROMPT (
    set "PROMPT=%PROMPT%__REZUP_PROMPT__"
)

if defined __REZUP_RUN_SCRIPT__ (
    call "__REZUP_SCRIPT__"
)

exit %errorlevel%
