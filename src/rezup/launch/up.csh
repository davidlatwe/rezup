
if ( "__REZUP_DO__" == "script" ) then
    source __REZUP_DO_SCRIPT__
    exit $status
endif
if ( "__REZUP_DO__" == "command" ) then
    __REZUP_DO_COMMAND__
    exit $status
endif

__REZUP_SHELL__ -i
