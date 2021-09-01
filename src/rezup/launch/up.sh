
if [ -z "${REZUP_DISABLE_PROMPT-}" ] ; then
    PS1="__REZUP_PROMPT__${PS1-}"
    export PS1
fi

# This should detect bash and zsh, which have a hash command that must
# be called to get it to forget past commands.  Without forgetting
# past commands the $PATH changes we made may not be respected
if [ -n "${BASH-}" ] || [ -n "${ZSH_VERSION-}" ] ; then
    hash -r 2>/dev/null
fi


if [ -n "${__REZUP_SCRIPT__-}" ] ; then
    # shellcheck source=/dev/null
    . "${__REZUP_SCRIPT__}"
fi
if [ -n "${__REZUP_COMMAND__-}" ] ; then
    # shellcheck source=/dev/null
    "${__REZUP_COMMAND__}"
fi
