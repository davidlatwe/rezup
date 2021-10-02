
if [ -n "${__REZUP_SCRIPT__-}" ] ; then
    # shellcheck source=/dev/null
    . "${__REZUP_SCRIPT__}"
    exit $?
fi
if [ -n "${__REZUP_COMMAND__-}" ] ; then
    # shellcheck source=/dev/null
    "${__REZUP_COMMAND__}"
    exit $?
fi

$_REZUP_SHELL -i
