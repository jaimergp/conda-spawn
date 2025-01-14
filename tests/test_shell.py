import signal
import sys

import pytest
from conda_spawn.shell import PosixShell, PowershellShell

from subprocess import PIPE

@pytest.mark.skipif(sys.platform == "win32", reason="Pty's only available on Unix")
def test_posix_shell():
    proc = PosixShell().spawn_tty(sys.prefix)
    proc.sendline("env")
    proc.expect("CONDA_SPAWN")
    proc.sendline("echo $CONDA_PREFIX")
    proc.expect(sys.prefix)
    proc.kill(signal.SIGINT)


@pytest.mark.skipif(sys.platform != "win32", reason="Powershell only tested on Windows")
def test_powershell():
    with PowershellShell().spawn_popen(sys.prefix, stdout=PIPE, text=True) as proc:
        out, _ = proc.communicate("env")
        proc.kill()
        assert not proc.poll()
        assert "CONDA_SPAWN" in out
        assert "CONDA_PREFIX" in out
