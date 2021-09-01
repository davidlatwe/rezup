@echo off

if not defined PROMPT (
    set "PROMPT=$P$G"
)
if not defined REZUP_DISABLE_PROMPT (
    set "PROMPT=__REZUP_PROMPT__%PROMPT%"
)

if defined __REZUP_SCRIPT__ (
    call %__REZUP_SCRIPT__%
)
if defined __REZUP_COMMAND__ (
    %__REZUP_COMMAND__%
)
