
if [ -z "${REZUP_DISABLE_PROMPT-}" ] ; then
    PS1="__REZUP_PROMPT__${PS1-}"
    export PS1
fi


if [ -n "${__REZUP_RUN_SCRIPT__-}" ] ; then
    # shellcheck source=/dev/null
    . "__REZUP_SCRIPT__"
else
    __REZUP_SHELL__
fi

exit $?
