
import os
import sys
import click
import logging
from . import get_rezup_version, __version__
from .container import Container, iter_containers


_default_cname = Container.DEFAULT_NAME
_log = logging.getLogger("rezup")


def _disable_rezup_if_entered(ctx):
    _con = os.getenv("REZUP_CONTAINER")
    if _con:
        print("Not allowed inside container, please exit first. "
              "(current: %s)" % _con)
        ctx.exit(1)


def run():
    """CLI entry point.

    ```
    $ rezup --help
    ```
    """
    obj = {
        "job": None,
        "wait": None,
    }

    # for fast access
    if len(sys.argv) == 1:
        sys.argv += ["use", _default_cname]

    # consume all args after '--' so no need to rely on problem prone 'nargs'
    #   as container command
    if sys.argv[1] == "use" and "--" in sys.argv:
        obj["job"] = _parse_use_cmd()

    # enter
    _log.setLevel(logging.INFO)
    cli(obj=obj)


def _parse_use_cmd():
    """Parse job command from sys.argv for command 'rezup use -- [COMMAND]'
    """
    double_dash_pos = sys.argv.index("--")
    args = sys.argv[double_dash_pos + 1:]
    sys.argv[:] = sys.argv[:double_dash_pos]
    return args


def _opt_callback_debug_logging(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    _log.setLevel(logging.DEBUG)


def _opt_callback_show_latest(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    click.echo(fetch_latest_version_from_pypi())
    ctx.exit()


# for reusable across commands
_cli_debug_option = click.option(
    "-D", "--debug",
    help="Show debug level logging messages.",
    is_eager=True,
    is_flag=True,
    expose_value=False,
    callback=_opt_callback_debug_logging,
)


@click.group()
@click.version_option(
    __version__,
    "-V", "--version",
    message=get_rezup_version(),
)
@click.option(
    "-L", "--latest",
    help="Show latest version of rezup(api) in PyPI and exit.",
    is_eager=True,
    is_flag=True,
    expose_value=False,
    callback=_opt_callback_show_latest,
)
@_cli_debug_option
@click.help_option("-h", "--help")
@click.pass_context
def cli(ctx):
    """Rez launching environment manager

    A Rez production virtual environment management tool, which allows safe
    environment update without any interruption. Plus a convenient virtual
    environment setup interface.

    https://github.com/davidlatwe/rezup

    """
    _disable_rezup_if_entered(ctx)


@cli.command(options_metavar="[NAME] [OPTIONS] [-- commands..]")
@click.argument("name", nargs=1, default=_default_cname, metavar="")
@click.option("-l", "--local", is_flag=True,
              help="Enforce using local container")
@click.option("-n", "--no-wait", is_flag=True,
              help="Not waiting '-- {command}' to complete")
@_cli_debug_option
@click.help_option("-h", "--help")
@click.pass_context
def use(ctx, name, local, no_wait):
    """Step into a container.

    This will open a sub-shell which has Rez venv ready to use. Simply
    type 'exit' when finished.

    Examples:

        \b
        - for quick start, auto use default container '.main'
        $ rezup

        \b
        - use container 'foo'
        $ rezup use foo

        \b
        - ignore remote and only use local container
        $ rezup use foo --local

        \b
        - use foo and run command (non-interactive session)
        $ rezup use foo -- {command}

        \b
        - not waiting the command process to complete
        $ rezup use foo --no-wait -- {command}

    \f
    Args:
        ctx (click.Context): click's internal context object
        name (str): container name
        local (bool): ignore remote and use local container
        no_wait (bool): not waiting '-- {command}' to complete

    """
    ctx.obj["wait"] = not no_wait

    container = Container(name, force_local=local)
    revision = container.get_latest_revision()

    if revision:
        ctx.exit(
            revision.use(command=ctx.obj["job"], wait=ctx.obj["wait"])
        )
    else:
        if container.is_exists():
            _log.error(
                "Container '%s' exists but has no valid revision: %s"
                % (container.name(), container.path())
            )
            ctx.exit(1)

        elif container.name() != Container.DEFAULT_NAME:
            _log.error(
                "Container '%s' not exist, use 'rezup add' to create."
                % container.name()
            )
            ctx.exit(1)

        else:
            # for quick first run
            _log.info("Creating container automatically for first run..")
            ctx.invoke(add, name=name)


@cli.command(options_metavar="[NAME] [OPTIONS]")
@click.argument("name", nargs=1, default=_default_cname, metavar="")
@click.option("-r", "--remote", is_flag=True, help="Add as remote container")
@click.option("-s", "--skip-use", is_flag=True, help="Add container and exit.")
@_cli_debug_option
@click.help_option("-h", "--help")
@click.pass_context
def add(ctx, name=_default_cname, remote=False, skip_use=False):
    """Add one container revision.

    This will create a new container revision (a new Rez venv setup) with
    corresponding recipe file.

    Examples:

        \b
        - create & use new rev for local container '.main' (with ~/rezup.toml)
        $ rezup add

        \b
        - create & use new rev for local container 'foo' (with ~/rezup.foo.toml)
        $ rezup add foo

        \b
        - create new rev for remote container
        $ rezup add --remote --skip-use

    \f
    Args:
        ctx (click.Context): click's internal context object
        name (str): container name
        remote (bool): add a remote revision
        skip_use (bool): add revision and exit

    """
    if remote:
        _log.info("Creating remote container..")
        container = Container.create(name)
        if not container.is_remote():
            _log.error("Remote root is not set.")
            ctx.exit(1)
    else:
        _log.info("Creating local container..")
        container = Container.create(name, force_local=True)

    revision = container.new_revision()

    if not skip_use:
        ctx.exit(
            revision.use(command=ctx.obj["job"], wait=ctx.obj["wait"])
        )


@cli.command()
@click.argument("name", nargs=1)
@_cli_debug_option
@click.help_option("-h", "--help")
def drop(name):
    """Remove a container.

    Remove entire container from disk. This command isn't ready yet, use
    with caution.

    Examples:

        \b
        - remove container foo
        $ rezup drop foo

    \f
    Args:
        name (str): container name

    """
    container = Container(name)
    container.purge()


@cli.command()
@click.argument("name", nargs=1, required=False)
@_cli_debug_option
@click.help_option("-h", "--help")
def status(name=None):
    """Show status of containers.

    Displaying some useful info about current visible containers..

    Examples:

        \b
        - list containers and info
        $ rezup status

        \b
        - show detailed info of specific container
        $ rezup status foo

    \f
    Args:
        name (str): show status of specific container if name given

    """
    if name is None:
        # show overall status

        print("   Name   | Is Remote | Rev Count | Root     ")
        print("---------------------------------------------")
        stat_line = "{name: ^10} {remote: ^11} {rev_count: ^11} {root}"

        for con in iter_containers():
            stat = {
                "name": con.name(),
                "remote": "O" if con.is_remote() else "-",
                "rev_count": len(list(con.iter_revision())),
                "root": con.root(),
            }
            print(stat_line.format(**stat))

    else:
        # show specific container info

        con = Container(name)
        if con.is_remote():
            local_con = Container(name, force_local=True)
            remote_con = con
        else:
            local_con = con
            remote_con = None

        print("Container: %s" % name)

        if remote_con is None and not local_con.is_exists():
            print("NOT EXISTS.")
            return

        print("    Local: %s" % local_con.path())
        print("   Remote: %s" % (remote_con.path() if remote_con else "-"))
        print("")
        print(" Local | Remote |   Rez   |       Date      | Timestamp    ")
        print("-----------------------------------------------------------")
        info_line = "{l: ^7}|{r: ^8}|{rez: ^9}| {date} | {time}"

        # sort and paring revisions
        # https://gist.github.com/davidlatwe/a729e06c54b712db72516d17fdbcbe98
        revs = list(local_con.iter_revision())
        revs += list(remote_con.iter_revision()) if remote_con else []
        sorted_revs = sorted(
            revs, key=lambda r: (r.timestamp(), -r.is_remote())
        )
        paired_revs = {"L": [], "R": []}
        for rev in sorted_revs:
            if rev.is_remote():
                paired_revs["R"].append(rev)
                paired_revs["L"].append(None)
            else:
                if paired_revs["R"] and paired_revs["R"][-1] == rev:
                    paired_revs["L"][-1] = rev
                else:
                    paired_revs["R"].append(None)
                    paired_revs["L"].append(rev)

        # print out
        for i, local in enumerate(paired_revs["L"]):
            remote = paired_revs["R"][i]

            if local is None and remote is None:
                continue  # not likely to happen

            data = local or remote
            info = {
                "l": "O" if local else "-",
                "r": "O" if remote else "-",
                "rez": (local.get_rez_version() or "?") if local else "-",
                "date": data.time_str(),
                "time": data.dirname(),
            }
            print(info_line.format(**info))
        print("")


def fetch_latest_version_from_pypi():
    """Parse latest `rezup-api` package version from PyPI.

    ```
    $ rezup --latest
    ```
    """
    import re

    try:
        from urllib.request import urlopen  # noqa, py3
    except ImportError:
        from urllib import urlopen    # noqa, py2

    name = "rezup-api"

    _pypi_url = "https://pypi.python.org/simple/{}".format(name)
    _regex_version = re.compile(".*{}-(.*)\\.tar\\.gz".format(name))

    f = urlopen(_pypi_url)
    text = f.read().decode("utf-8")
    f.close()

    latest_str = ""
    for line in text.split():
        result = _regex_version.search(line)
        if result:
            latest_str = result.group(1)

    if latest_str:
        return latest_str

    return "Failed to fetch latest %s version from PyPI.." % name
