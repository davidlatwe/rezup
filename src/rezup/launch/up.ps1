
if ($env:REZUP_PROMPT) {
    function global:_old_virtual_prompt {
        ""
    }
    $function:_old_virtual_prompt = $function:prompt

    function global:prompt {
        # Add the custom prefix to the existing prompt
        $previous_prompt_value = & $function:_old_virtual_prompt
        ($env:REZUP_PROMPT + $previous_prompt_value)
    }
}

if ($env:__REZUP_SCRIPT__) {
    & $env:__REZUP_SCRIPT__
}
if ($env:__REZUP_COMMAND__) {
    $env:__REZUP_COMMAND__
}
exit $LastExitCode
