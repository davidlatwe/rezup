
# Command Line Interface

## Commands

!!! tip "debug logging"
    You can always add `--debug` or `-D` flag into any command to display debug message.

### $ `rezup use`

!!! example "Quick start, auto use default container '.main'"
    The command `use` can be omitted
    ```shell
    $ rezup
    ```

!!! example "Use container 'foo'"
    ```shell
    $ rezup use foo
    ```

!!! example "Ignore remote and only use local container"
    If local and remote root are both set for the container, remote will be sourced first by default even local container has newer revision. So sometimes you may want to ignore the remote.
    ```shell
    $ rezup use foo --local
    ```

!!! example "Use 'foo' and run command"
    Everything after `--` will be passed as command.
    ```shell
    $ rezup use foo -- rez-env
    ```

### $ `rezup add`

!!! example "Create & use new revision for local container '.main'"
    ```shell
    $ rezup add
    ```

!!! example "Create & use new revision for local container 'foo'"
    ```shell
    $ rezup add foo
    ```

!!! example "Create new revision for remote container '.main' and exit"
    ```shell
    $ rezup add --remote --skip-use
    ```

### $ `rezup drop`

!!! danger "Not ready for prime-time"
    This command actually is not fully functional yet.

### $ `rezup status`

!!! example "List containers and info"
    ```shell
    $ rezup status
    ```

!!! example "Show detailed info of specific container"
    ```shell
    $ rezup status foo
    ```

--8<-- "src/rezup/launch/README.md"
