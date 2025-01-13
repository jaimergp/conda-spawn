from __future__ import annotations

import fcntl
import os
import shlex
import shutil
import signal
import struct
import sys
import termios
from tempfile import NamedTemporaryFile
from logging import getLogger
from pathlib import Path
from typing import Iterable

import pexpect
from conda import activate


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

    def spawn(self, prefix: Path, command: Iterable[str] | None = None) -> int:
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

        script, prompt = self.script_and_prompt(prefix)
        executable, args = self.executable_and_args()
        size = shutil.get_terminal_size()

        child = pexpect.spawn(
            executable,
            args,
            env=self.env(),
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
                f.write(script)
            signal.signal(signal.SIGWINCH, _sigwinch_passthrough)
            # Source the activation script. We do this in a single line for performance.
            # It's slower to send several lines than paying the IO overhead.
            child.sendline(f' . "{f.name}" && PS1="{prompt}${{PS1:-}}" && stty echo')
            os.read(child.child_fd, 4096)  # consume buffer before interact
            if Path(executable).name == "zsh":
                child.expect('\r\n')
            if command:
                child.sendline(shlex.join(command))
            child.interact()
        finally:
            os.unlink(f.name)
        return child.wait()

    def script_and_prompt(self, prefix: Path) -> tuple[str, str]:
        activator = self.Activator(["activate", str(prefix)])
        conda_default_env = os.getenv("CONDA_DEFAULT_ENV", activator._default_env(str(prefix)))
        prompt = activator._prompt_modifier(str(prefix), conda_default_env)
        script = activator.execute()
        lines = []
        for line in script.splitlines(keepends=True):
            if "PS1=" in line:
                continue
            lines.append(line)
        script = "".join(lines)
        return script, prompt
    
    def executable_and_args(self) -> tuple[str, list[str]]:
        # TODO: Customize which shell gets used; this below is the default!
        return os.environ.get("SHELL", "/bin/bash"), ["-l", "-i"]
    
    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["CONDA_SPAWN"] = "1"
        return env

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
