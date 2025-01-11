from __future__ import annotations

import fcntl
import os
import shutil
import signal
import struct
import sys
import termios
import time
from tempfile import NamedTemporaryFile
from logging import getLogger
from pathlib import Path

import pexpect
from conda import activate
from conda.base.context import context

log = getLogger(f"conda.{__name__}")


class Shell:
    def spawn(self, prefix: Path) -> int:
        """
        Creates a new shell session with the conda environment at `path`
        already activated and waits for the shell session to finish.

        Returns the exit code of such process.
        """
        raise NotImplementedError


class PosixShell(Shell):
    Activator = activate.PosixActivator

    def spawn(self, prefix: Path, command: str | None = None) -> int:
        def _sigwinch_passthrough(sig, data):
            # NOTE: Taken verbatim from pexpect's .interact() docstring.
            # Check for buggy platforms (see pexpect.setwinsize()).
            if "TIOCGWINSZ" in dir(termios):
                TIOCGWINSZ = termios.TIOCGWINSZ
            else:
                TIOCGWINSZ = 1074295912  # assume
            s = struct.pack("HHHH", 0, 0, 0, 0)
            a = struct.unpack("HHHH", fcntl.ioctl(sys.stdout.fileno(), TIOCGWINSZ, s))
            child.setwinsize(a[0], a[1])

        activator = self.Activator(["activate", str(prefix)])
        activator._parse_and_set_args()
        script = activator.activate()
        env = os.environ.copy()
        env["CONDA_SPAWN"] = "1"
        size = shutil.get_terminal_size()
        # TODO: Customize which shell gets used; this below is the default!
        executable = os.environ.get("SHELL", "/bin/bash")
        args = ["-l", "-i"]
        child = pexpect.spawn(
            executable,
            args,
            env=env,
            echo=False,
            dimensions=(size.lines, size.columns),
        )
        try:
            with NamedTemporaryFile(
                prefix="conda-spawn-",
                suffix=".sh",
                delete=False,
                mode="w",
            ) as f:
                f.write(script.replace("PS1", "_PS1"))
            signal.signal(signal.SIGWINCH, _sigwinch_passthrough)
            # This exact sequence of commands is very deliberate!
            # 1. Source the activation script. We do this in a single line for performance.
            # It's slower to send several lines than paying the IO overhead.
            child.sendline(f" . '{f.name}'")
            # 2. Wait for a newline; this swallows the echo (echo=False doesn't work?)
            child.expect('\r\n')
            # 3. Set PS1 in shell directly. Otherwise we might lose it!
            child.sendline(' PS1="(conda-spawn) ${PS1:-}"')
            # 4. Restore echo AND wait for newline, in that order.
            # Other order would leak the PS1 command to output.
            child.setecho(True)
            child.expect('\r\n')
            # 5. Here we can send any program to start
            if command:
                child.sendline(command)
            child.interact()
        finally:
            os.unlink(f.name)
        return child.wait()


class CshShell(Shell):
    def spawn(self, prefix: Path) -> int: ...


class XonshShell(Shell):
    def spawn(self, prefix: Path) -> int: ...


class FishShell(Shell):
    def spawn(self, prefix: Path) -> int: ...


class CmdExeShell(Shell):
    def spawn(self, prefix: Path) -> int: ...


class PowershellShell(Shell):
    def spawn(self, prefix: Path) -> int: ...


SHELLS: dict[str, type[Shell]] = {
    "posix": PosixShell,
    "ash": PosixShell,
    "bash": PosixShell,
    "dash": PosixShell,
    "zsh": PosixShell,
    "csh": CshShell,
    "tcsh": CshShell,
    "xonsh": XonshShell,
    "cmd.exe": CmdExeShell,
    "fish": FishShell,
    "powershell": PowershellShell,
}


def detect_shell_class():
    return PosixShell
