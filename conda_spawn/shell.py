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
    def spawn(self, prefix: Path) -> int:
        """
        Creates a new shell session with the conda environment at `path`
        already activated and waits for the shell session to finish.

        Returns the exit code of such process.
        """
        raise NotImplementedError


class PosixShell(Shell):
    Activator = activate.PosixActivator
    tmp_suffix = ".sh"

    def spawn_tty(self, prefix: Path, command: Iterable[str] | None = None) -> pexpect.spawn:
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
                suffix=self.tmp_suffix,
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
                child.expect("\r\n")
            if command:
                child.sendline(shlex.join(command))
            if sys.stdin.isatty():
                child.interact()
            return child
        finally:
            os.unlink(f.name)
    
    def spawn(self, prefix: Path, command: Iterable[str] | None = None) -> int:
        return self.spawn_tty(prefix, command).wait()

    def script_and_prompt(self, prefix: Path) -> tuple[str, str]:
        activator = self.Activator(["activate", str(prefix)])
        conda_default_env = os.getenv(
            "CONDA_DEFAULT_ENV", activator._default_env(str(prefix))
        )
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
    def spawn(self, prefix: Path, command: Iterable[str] | None = None) -> int: ...


class XonshShell(Shell):
    def spawn(self, prefix: Path, command: Iterable[str] | None = None) -> int: ...


class FishShell(Shell):
    def spawn(self, prefix: Path, command: Iterable[str] | None = None) -> int: ...


class PowershellShell(Shell):
    Activator = activate.PowerShellActivator
    tmp_suffix = ".ps1"

    def spawn_popen(self, prefix: Path, command: Iterable[str] | None = None, **kwargs) -> subprocess.Popen:
        executable, args = self.executable_and_args()
        script, _ = self.script_and_prompt(prefix)
        try:
            with NamedTemporaryFile(
                prefix="conda-spawn-",
                suffix=self.tmp_suffix,
                delete=False,
                mode="w",
            ) as f:
                f.write(f"{script}\r\n")
                if command:
                    command = subprocess.list2cmdline(command)
                    f.write(f"echo {command}\r\n")
                    f.write(f"{command}\r\n")
            args.append(f.name)
            return subprocess.Popen([executable, *args], env=self.env(), **kwargs)
        finally:
            self._tmpfile = f.name

    def spawn(self, prefix: Path, command: Iterable[str] | None = None) -> int:
        proc = self.spawn_popen(prefix, command)
        proc.communicate()
        return proc.wait()

    def script_and_prompt(self, prefix: Path) -> tuple[str, str]:
        activator = self.Activator(["activate", str(prefix)])
        conda_default_env = os.getenv(
            "CONDA_DEFAULT_ENV", activator._default_env(str(prefix))
        )
        prompt_mod = activator._prompt_modifier(str(prefix), conda_default_env)
        script = activator.execute()
        script += (
            "\r\n$old_prompt = $function:prompt\r\n"
            f'function prompt {{"{prompt_mod}$($old_prompt.Invoke())"}};'
        )
        return script, ""

    def executable_and_args(self) -> tuple[str, list[str]]:
        # TODO: Customize which shell gets used; this below is the default!
        return "powershell", ["-NoLogo", "-NoExit", "-File"]

    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["CONDA_SPAWN"] = "1"
        return env
    
    def __del__(self):
        if getattr(self, "_tmpfile", None):
            os.unlink(self._tmpfile)


class CmdExeShell(PowershellShell):
    Activator = activate.CmdExeActivator
    tmp_suffix = ".bat"

    def script_and_prompt(self, prefix: Path) -> tuple[str, str]:
        activator = self.Activator(["activate", str(prefix)])
        conda_default_env = os.getenv(
            "CONDA_DEFAULT_ENV", activator._default_env(str(prefix))
        )
        prompt_mod = activator._prompt_modifier(str(prefix), conda_default_env)
        script = "@ECHO OFF\r\n"
        script += activator.execute()
        script += f"\r\n@PROMPT {prompt_mod}$P$G"
        script += "@ECHO ON\r\n"
        return script, ""

    def executable_and_args(self) -> tuple[str, list[str]]:
        # TODO: Customize which shell gets used; this below is the default!
        return "cmd", ["/K"]


SHELLS: dict[str, type[Shell]] = {
    "ash": PosixShell,
    "bash": PosixShell,
    "cmd.exe": CmdExeShell,
    "cmd": CmdExeShell,
    "csh": CshShell,
    "dash": PosixShell,
    "fish": FishShell,
    "posix": PosixShell,
    "powershell": PowershellShell,
    "tcsh": CshShell,
    "xonsh": XonshShell,
    "zsh": PosixShell,
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
