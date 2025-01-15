from __future__ import annotations

from conda import plugins

from . import cli


@plugins.hookimpl
def conda_subcommands():
    yield plugins.CondaSubcommand(
        name="spawn",
        summary="Activate conda environments in new shell processes.",
        action=cli.execute,
        configure_parser=cli.configure_parser,
    )
