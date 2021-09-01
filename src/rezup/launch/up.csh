
set newline='\
'

set env_name = '__REZUP_PROMPT__'

if ( $?REZUP_DISABLE_PROMPT ) then
    if ( $REZUP_DISABLE_PROMPT == "" ) then
        set do_prompt = "1"
    else
        set do_prompt = "0"
    endif
else
    set do_prompt = "1"
endif

if ( $do_prompt == "1" ) then
    # Could be in a non-interactive environment,
    # in which case, $prompt is undefined and we wouldn't
    # care about the prompt anyway.
    if ( $?prompt ) then
        if ( "$prompt:q" =~ *"$newline:q"* ) then
            :
        else
            set prompt = "$env_name:q$prompt:q"
        endif
    endif
endif

unset env_name
unset do_prompt

rehash

if ( $?__REZUP_SCRIPT__ ) then
    source $__REZUP_SCRIPT__
endif
if ( $?__REZUP_COMMAND__ ) then
    $__REZUP_COMMAND__
endif
