
$VIRTUAL_ENV_PROMPT = "__REZUP_PROMPT__"
if not $VIRTUAL_ENV_PROMPT:
    del $VIRTUAL_ENV_PROMPT

if $__REZUP_SCRIPT__:
    source $__REZUP_SCRIPT__
if $__REZUP_COMMAND__:
    $__REZUP_COMMAND__
