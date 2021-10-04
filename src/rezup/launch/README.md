
## Shell Prompt

You may customize the prompt with environ var `REZUP_PROMPT`, to get the container name for custom prompt, use env var `REZUP_CONTAINER`.


## Set Prompts in Unix Shell

Due to the rcfiles, I cannot change prompt from Rezup launch script.
So unless copying all rcfiles into a temp dir and modify prompt from there (just like how Rez changing prompt in sub-shell), you have to do this in your own `~/.bashrc` or `~/.cshrc`.

### bash, zsh

```bash
# ~/.bashrc
if [ -n "${REZUP_PROMPT-}" ] ; then
    export PS1=$REZUP_PROMPT$PS1
fi
```

### csh, tcsh
```shell
# ~/.cshrc
if ( ! $?prompt ) then
    set prompt="% "
endif
if ( $?REZUP_PROMPT ) then
    set prompt="${REZUP_PROMPT}${prompt}"
endif
```

## Shell detection

Rezup uses an excellent tool [`shellingham`](https://github.com/sarugaku/shellingham/tree/1.3.1) to detect current shell for spawning sub-shell. This works great on Windows, however on POSIX, `shellingham` seems detecting shell with env `$SHELL` in most cases, which means mostly what you get is the login shell, not the current shell that is being used.

For example:

```shell
$ python3 -c "import shellingham;print(shellingham.detect_shell())"
$ ('bash', '/bin/bash')
$ csh
% python3 -c "import shellingham;print(shellingham.detect_shell())"
% ('bash', '/bin/bash')
```

https://unix.stackexchange.com/q/45458

To overcome this, use env `REZUP_DEFAULT_SHELL` to set the shell you want.

## Notes

* Remember to convert line ending to Unix format if shell scripts have been edited on Windows. Or may get error like `^M: Command not found`.
* May get error like `Unmatched "` in `csh` shell when the prompt contains linebreak.
