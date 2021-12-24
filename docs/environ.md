
# Environment Variables

|Name|Description|
| --- | --- |
|REZUP_ROOT_LOCAL|Root path of local containers, if not defined in [Recipe](../container#root), default is `~/.rezup`|
|REZUP_ROOT_REMOTE|Root path of remote containers, if not defined in [Recipe](../container#root)|
|REZUP_DEFAULT_SHELL|Specify shell to use. See [Command](../command#shell-detection).|
|REZUP_PROMPT|For customizing shell prompt, optional. See [Command](../command#shell-prompt).|
|REZUP_CONTAINER|Auto set, for customizing shell prompt. See [Command](../command#shell-prompt).|
|REZUP_USING_REMOTE|Auto set, indicating where the container was sourced from.|
|REZUP_EDIT_IN_PRODUCTION|Enable production privilege for Rez that was installed in edit mode.|
|REZUP_TEST_KEEP_TMP|Preserve temp dirs in tests.|
