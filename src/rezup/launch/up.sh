
if [ -z "${REZUP_DISABLE_PROMPT-}" ] ; then
    PS1="${PS1-}__REZUP_PROMPT__"
    export PS1
fi


if [ -n "${__REZUP_RUN_SCRIPT__-}" ] ; then
    # shellcheck source=/dev/null
    . "__REZUP_SCRIPT__"
    exit $?
fi
