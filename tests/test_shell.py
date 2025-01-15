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


@pytest.fixture(scope="session")
def ca_certificates_env(session_tmp_env):
    with session_tmp_env("ca-certificates", "--quiet") as prefix:
        yield prefix


@pytest.mark.skipif(sys.platform == "win32", reason="Only tested on Unix")
def test_hooks_integration_posix(ca_certificates_env, tmp_path):
    hook = f"{sys.executable} -m conda spawn --hook --shell posix -p '{ca_certificates_env}'"
    script = f'eval "$({hook})"\nenv | sort'
    script_path = tmp_path / "script-eval.sh"
    script_path.write_text(script)

    out = check_output(["bash", script_path], text=True)
    print(out)
    assert str(ca_certificates_env) in out


@pytest.mark.skipif(sys.platform != "win32", reason="Powershell only tested on Windows")
def test_hooks_integration_powershell(ca_certificates_env, tmp_path):
    hook = f"{sys.executable} -m conda spawn --hook --shell powershell -p {ca_certificates_env}"
    script = f"{hook} | Out-String | Invoke-Expression\r\nls env:"
    script_path = tmp_path / "script-eval.ps1"
    script_path.write_text(script)

    out = check_output(["powershell", "-NoLogo", "-File", script_path], text=True)
    print(out)
    assert str(ca_certificates_env) in out


@pytest.mark.skipif(sys.platform != "win32", reason="Cmd.exe only tested on Windows")
def test_hooks_integration_cmd(ca_certificates_env, tmp_path):
    hook = (
        f"{sys.executable} -m conda spawn --hook --shell cmd -p {ca_certificates_env}"
    )
    script = f"FOR /F \"tokens=*\" %%g IN ('{hook}') do @CALL %%g\r\nset"
    script_path = tmp_path / "script-eval.bat"
    script_path.write_text(script)

    out = check_output(["cmd", "/D", "/C", script_path], text=True)
    print(out)
    assert str(ca_certificates_env) in out
