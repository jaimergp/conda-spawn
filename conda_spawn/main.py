""" """

from __future__ import annotations
from os.path import expanduser, expandvars, abspath
from pathlib import Path
from typing import Type, Iterable

from conda.base.constants import ROOT_ENV_NAME
from conda.base.context import context, locate_prefix_by_name
from conda.exceptions import DirectoryNotACondaEnvironmentError

from .exceptions import ShellNotSupported
from .shell import SHELLS, Shell, detect_shell_class


def spawn(
    prefix: Path, shell_cls: Shell | None = None, command: Iterable[str] | None = None
) -> int:
    if shell_cls is None:
        shell_cls = detect_shell_class()
    return shell_cls(prefix).spawn(command=command)


def hook(prefix: Path, shell_cls: Shell | None = None) -> int:
    if shell_cls is None:
        shell_cls = detect_shell_class()
    script = shell_cls(prefix).script()
    prompt = shell_cls(prefix).prompt()
    print(script)
    print(prompt)
    return 0


def environment_speficier_to_path(
    name: str | None = None,
    prefix: str | Path | None = None,
) -> Path:
    if sum([bool(x) for x in (name, prefix)]) != 1:
        raise ValueError("Please provide only name or prefix.")
    if name in (ROOT_ENV_NAME, "root"):
        return Path(context.root_prefix)
    if name:
        return Path(locate_prefix_by_name(name))

    prefix = Path(abspath(expanduser(expandvars((prefix)))))
    if (prefix / "conda-meta" / "history").is_dir():
        raise DirectoryNotACondaEnvironmentError(prefix)
    return prefix


def shell_specifier_to_shell(name: str | None = None) -> Type[Shell]:
    if name is None:
        return detect_shell_class()

    try:
        return SHELLS[name]
    except KeyError:
        raise ShellNotSupported(name)
