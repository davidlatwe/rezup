@echo off

if not defined PROMPT (
    set "PROMPT=$P$G"
)
if defined REZUP_PROMPT (
    set "PROMPT=%REZUP_PROMPT%%PROMPT%"
)
