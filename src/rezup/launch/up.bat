@echo off

if not defined PROMPT (
    set "PROMPT=$P$G"
)
if defined REZUP_PROMPT (
    set "PROMPT=%REZUP_PROMPT%%PROMPT%"
)

if defined __REZUP_SCRIPT__ (
    call %__REZUP_SCRIPT__%
    exit %errorlevel%
)
if defined __REZUP_COMMAND__ (
    %__REZUP_COMMAND__%
    exit %errorlevel%
)
