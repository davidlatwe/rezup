

if test -z "$REZUP_DISABLE_PROMPT"
    # Copy the current `fish_prompt` function as `_old_fish_prompt`.
    functions -c fish_prompt _old_fish_prompt

    function fish_prompt
        # Run the user's prompt first; it might depend on (pipe)status.
        set -l prompt (_old_fish_prompt)

        printf '%s%s' '__REZUP_PROMPT__' (set_color normal)

        string join -- \n $prompt # handle multi-line prompts
    end
end

if test -n '__REZUP_SCRIPT__'
    . "${__REZUP_SCRIPT__}"
end
if test -n '__REZUP_COMMAND__'
    "${__REZUP_COMMAND__}"
end
