
if (!$env:REZUP_DISABLE_PROMPT) {
    function global:_old_virtual_prompt {
        ""
    }
    $function:_old_virtual_prompt = $function:prompt

    function global:prompt {
        # Add the custom prefix to the existing prompt
        $previous_prompt_value = & $function:_old_virtual_prompt
        ($previous_prompt_value + "__REZUP_PROMPT__")
    }
}

if ($env:__REZUP_RUN_SCRIPT__) {
    & "__REZUP_SCRIPT__"
}

exit $LastExitCode
