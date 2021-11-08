
## Environment Variables

|Name|Description|
| --- | --- |
|REZUP_ROOT_LOCAL|Local root of all containers and metadata, default is `~/.rezup`|
|REZUP_ROOT_REMOTE|Remote root of all containers but only recipe file|
|REZUP_DEFAULT_SHELL|Specify shell to use. See [launch/README](src/rezup/launch/README.md#shell-detection).|
|REZUP_PROMPT|For customizing shell prompt, optional. See [launch/README](src/rezup/launch/README.md#shell-prompt).|
|REZUP_CONTAINER|Auto set, for customizing shell prompt. See [launch/README](src/rezup/launch/README.md#shell-prompt).|
|REZUP_USING_REMOTE|Auto set, indicating where the container was sourced from.|
|REZUP_TEST_KEEP_TMP|Preserve temp dirs in tests.|
