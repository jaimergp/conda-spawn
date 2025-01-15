import signal
import sys

import pytest
from conda_spawn.shell import PosixShell, PowershellShell, CmdExeShell

from subprocess import PIPE, check_output


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


def test_hooks(conda_cli):
    out, err, rc = conda_cli("spawn", "--hook", "-p", sys.prefix)
    print(out)
    print(err, file=sys.stderr)
    assert not rc
    assert not err
    assert "CONDA_EXE" in out
    assert sys.prefix in out


def test_hooks_integration(conda_cli, tmp_env, tmp_path):
    on_win = sys.platform == "win32"
    with tmp_env("ca-certificates") as prefix:
        script_paths = []

        # Method 1 - copy pasted
        out, err, rc = conda_cli("spawn", "--hook", "-p", prefix)
        if on_win:
            script = f"{out}\r\nset"
            ext = ".bat"
        else:
            script = f"{out}\nenv | sort"
            ext = "sh"
        script_path = tmp_path / f"script-pasted.{ext}"
        script_path.write_text(script)
        script_paths.append(script_path)

        # Method 2 - eval equivalents
        if on_win:
            hook = f"{sys.executable} -m conda spawn --hook --shell cmd -p {prefix}"
            script = f'FOR /F "tokens=*" %%g IN (\'{hook}\') do @CALL %%g\r\nset'
            ext = ".bat"
        else:
            hook = f"{sys.executable} -m conda spawn --hook --shell posix -p '{prefix}'"
            script = f'eval "$({hook})"\nenv | sort'
            ext = "sh"
        script_path = tmp_path / f"script-eval.{ext}"
        script_path.write_text(script)
        script_paths.append(script_path)

        for script_path in script_paths:
            print(script_path)
            if on_win:
                out = check_output(["cmd", "/D", "/C", script_path], text=True)
            else:
                out = check_output(["bash", script_path], text=True)
            print(out)
            assert str(prefix) in out
