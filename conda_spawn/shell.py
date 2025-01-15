from __future__ import annotations

import os
import shlex
import shutil
import signal
import subprocess
import struct
import sys
from tempfile import NamedTemporaryFile
from logging import getLogger
from pathlib import Path
from typing import Iterable

if sys.platform != "win32":
    import fcntl
    import termios

    import pexpect

import shellingham
from conda import activate


log = getLogger(f"conda.{__name__}")


class Shell:
    Activator = ...

    def __init__(self, prefix: Path):
        self.prefix = prefix

    def spawn(self, prefix: Path) -> int:
        """
        Creates a new shell session with the conda environment at `path`
        already activated and waits for the shell session to finish.

        Returns the exit code of such process.
        """
        raise NotImplementedError

    def script(self) -> str:
        raise NotImplementedError

    def prompt(self) -> str:
        raise NotImplementedError

    def executable(self) -> str:
        raise NotImplementedError

    def args(self) -> tuple[str, ...]:
        raise NotImplementedError

    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["CONDA_SPAWN"] = "1"
        return env


class PosixShell(Shell):
    Activator = activate.PosixActivator
    default_shell = "/bin/sh"
    default_args = ("-l", "-i")

    def spawn(self, command: Iterable[str] | None = None) -> int:
        return self.spawn_tty(command).wait()

    def script(self) -> str:
        return self._script_and_prompt()[0]

    def prompt(self) -> str:
        return self._script_and_prompt()[1]

    def _script_and_prompt(self) -> tuple[str, str]:
        prefix_str = str(self.prefix)
        activator = self.Activator(["activate", prefix_str])
        conda_default_env = os.getenv(
            "CONDA_DEFAULT_ENV", activator._default_env(prefix_str)
        )
        prompt_mod = activator._prompt_modifier(prefix_str, conda_default_env)
        prompt = f'PS1="{prompt_mod}${{PS1:-}}"'
        script = activator.execute()
        lines = []
        for line in script.splitlines(keepends=True):
            if "PS1=" in line:
                continue
            lines.append(line)
        script = "".join(lines)
        return script, prompt

    def executable(self):
        return os.environ.get("SHELL", self.default_shell)

    def args(self):
        return self.default_args

    def spawn_tty(self, command: Iterable[str] | None = None) -> pexpect.spawn:
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

        script, prompt = self._script_and_prompt()
        size = shutil.get_terminal_size()
        executable = self.executable()

        child = pexpect.spawn(
            self.executable(),
            [*self.args()],
            env=self.env(),
            echo=False,
            dimensions=(size.lines, size.columns),
        )
        try:
            with NamedTemporaryFile(
                prefix="conda-spawn-",
                suffix=self.Activator.script_extension,
                delete=False,
                mode="w",
            ) as f:
                f.write(script)
            signal.signal(signal.SIGWINCH, _sigwinch_passthrough)
            # Source the activation script. We do this in a single line for performance.
            # (It's slower to send several lines than paying the IO overhead).
            # We set the PS1 prompt outside the script because it's otherwise invisible.
            # stty echo is equivalent to `child.setecho(True)` but the latter didn't work
            # reliably across all shells and OSs.
            child.sendline(f' . "{f.name}" && {prompt} && stty echo')
            os.read(child.child_fd, 4096)  # consume buffer before interact
            if Path(executable).name == "zsh":
                # zsh also needs this for a truly silent activation
                child.expect("\r\n")
            if command:
                child.sendline(shlex.join(command))
            if sys.stdin.isatty():
                child.interact()
            return child
        finally:
            os.unlink(f.name)


class BashShell(PosixShell):
    def executable(self):
        return "bash"


class ZshShell(PosixShell):
    def executable(self):
        return "zsh"


class CshShell(Shell):
    pass


class XonshShell(Shell):
    pass


class FishShell(Shell):
    pass


class PowershellShell(Shell):
    Activator = activate.PowerShellActivator

    def spawn_popen(
        self, command: Iterable[str] | None = None, **kwargs
    ) -> subprocess.Popen:
        script, prompt = self.script_and_prompt(self.prefix)
        try:
            with NamedTemporaryFile(
                prefix="conda-spawn-",
                suffix=self.Activator.script_extension,
                delete=False,
                mode="w",
            ) as f:
                f.write(f"{script}\r\n")
                f.write(f"{prompt}\r\n")
                if command:
                    command = subprocess.list2cmdline(command)
                    f.write(f"echo {command}\r\n")
                    f.write(f"{command}\r\n")
            return subprocess.Popen(
                [self.executable(), *self.args(), f.name], env=self.env(), **kwargs
            )
        finally:
            self._tmpfile = f.name

    def spawn(self, prefix: Path, command: Iterable[str] | None = None) -> int:
        proc = self.spawn_popen(prefix, command)
        proc.communicate()
        return proc.wait()

    def script(self) -> str:
        return self._script_and_prompt()[0]

    def prompt(self) -> str:
        return self._script_and_prompt()[1]

    def _script_and_prompt(self) -> tuple[str, str]:
        prefix_str = str(self.prefix)
        activator = self.Activator(["activate", prefix_str])
        conda_default_env = os.getenv(
            "CONDA_DEFAULT_ENV", activator._default_env(prefix_str)
        )
        prompt_mod = activator._prompt_modifier(prefix_str, conda_default_env)
        script = activator.execute()
        prompt = (
            "\r\n$old_prompt = $function:prompt\r\n"
            f'function prompt {{"{prompt_mod}$($old_prompt.Invoke())"}};'
        )
        return script, prompt

    def executable(self) -> str:
        return "powershell"

    def args(self) -> tuple[str, ...]:
        return ("-NoLogo", "-NoExit", "-File")

    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["CONDA_SPAWN"] = "1"
        return env

    def __del__(self):
        if getattr(self, "_tmpfile", None):
            os.unlink(self._tmpfile)


class CmdExeShell(PowershellShell):
    Activator = activate.CmdExeActivator

    def _script_and_prompt(self) -> tuple[str, str]:
        prefix_str = str(self.prefix)
        activator = self.Activator(["activate", prefix_str])
        conda_default_env = os.getenv(
            "CONDA_DEFAULT_ENV", activator._default_env(prefix_str)
        )
        prompt_mod = activator._prompt_modifier(prefix_str, conda_default_env)
        prompt = f'@SET "PROMPT={prompt_mod}$P$G"'
        script = "\r\n".join(
            [
                "@ECHO OFF",
                Path(activator.execute()).read_text(),
                "\r\n@ECHO ON\r\n",
            ]
        )
        return script, prompt

    def executable(self) -> str:
        return "cmd"

    def args(self) -> tuple[str, ...]:
        return ("/D", "/K")


SHELLS: dict[str, type[Shell]] = {
    "ash": PosixShell,
    "bash": BashShell,
    "cmd.exe": CmdExeShell,
    "cmd": CmdExeShell,
    "csh": CshShell,
    "dash": PosixShell,
    "fish": FishShell,
    "posix": PosixShell,
    "powershell": PowershellShell,
    "tcsh": CshShell,
    "xonsh": XonshShell,
    "zsh": ZshShell,
}


def default_shell_class():
    if sys.platform == "win32":
        return CmdExeShell
    return PosixShell


def detect_shell_class():
    try:
        name, _ = shellingham.detect_shell()
    except shellingham.ShellDetectionFailure:
        return default_shell_class()
    else:
        try:
            return SHELLS[name]
        except KeyError:
            log.warning("Did not recognize shell %s, returning default.", name)
            return default_shell_class()
