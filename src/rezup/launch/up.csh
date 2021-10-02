
if ( $?__REZUP_SCRIPT__ ) then
    source $__REZUP_SCRIPT__
    exit $status
endif
if ( $?__REZUP_COMMAND__ ) then
    $__REZUP_COMMAND__
    exit $status
endif
