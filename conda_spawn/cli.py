"""
conda pip subcommand for CLI
"""

from __future__ import annotations

import argparse

from conda.cli.conda_argparse import (
    add_parser_help,
    add_parser_prefix,
)


def configure_parser(parser: argparse.ArgumentParser):
    add_parser_help(parser)
    add_parser_prefix(parser, prefix_required=True)

    parser.add_argument(
        "command",
        nargs="*",
        help="Optional program and arguments to run after starting the shell.",
    )
    shell_group = parser.add_argument_group("Shell options")
    shell_group.add_argument(
        "-s",
        "--shell",
        help="Shell to use for the new session. "
        "If not specified, autodetect shell in use.",
    )


def execute(args: argparse.Namespace) -> int:
    from .main import spawn, environment_speficier_to_path, shell_specifier_to_shell

    prefix = environment_speficier_to_path(args.name, args.prefix)
    shell = shell_specifier_to_shell(args.shell)
    return spawn(prefix, shell, command=args.command)
