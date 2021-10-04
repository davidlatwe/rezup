
if [ "__REZUP_DO__" == "script" ] ; then
    . __REZUP_DO_SCRIPT__
    exit $?
fi
if [ "__REZUP_DO__" == "command" ] ; then
    __REZUP_DO_COMMAND__
    exit $?
fi

__REZUP_SHELL__ -i
