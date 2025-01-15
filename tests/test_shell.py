import signal
import sys

import pytest
from conda_spawn.shell import PosixShell, PowershellShell, CmdExeShell

from subprocess import PIPE


@pytest.mark.skipif(sys.platform == "win32", reason="Pty's only available on Unix")
def test_posix_shell():
    proc = PosixShell(sys.prefix).spawn_tty()
    proc.sendline("env")
    proc.expect("CONDA_SPAWN")
    proc.sendline("echo $CONDA_PREFIX")
    proc.expect(sys.prefix)
    proc.kill(signal.SIGINT)


@pytest.mark.skipif(sys.platform != "win32", reason="Powershell only tested on Windows")
def test_powershell():
    shell = PowershellShell(sys.prefix)
    with shell.spawn_popen(command=["ls", "env:"], stdout=PIPE, text=True) as proc:
        out, _ = proc.communicate()
        proc.kill()
        assert not proc.poll()
        assert "CONDA_SPAWN" in out
        assert "CONDA_PREFIX" in out


@pytest.mark.skipif(sys.platform != "win32", reason="Cmd.exe only tested on Windows")
def test_cmd():
    shell = CmdExeShell(sys.prefix)
    with shell.spawn_popen(command=["@SET"], stdout=PIPE, text=True) as proc:
        out, _ = proc.communicate()
        proc.kill()
        assert not proc.poll()
        assert "CONDA_SPAWN" in out
        assert "CONDA_PREFIX" in out
