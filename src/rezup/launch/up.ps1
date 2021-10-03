
if ("__REZUP_DO__" -eq "script") {
    & __REZUP_DO_SCRIPT__
    exit $LastExitCode
}
if ("__REZUP_DO__" -eq "command") {
    __REZUP_DO_COMMAND__
    exit $LastExitCode
}

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
