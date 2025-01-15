import sys


def test_cli(monkeypatch, conda_cli):
    monkeypatch.setattr(sys, "argv", ["conda", *sys.argv[1:]])
    out, err, _ = conda_cli("spawn", "-h", raises=SystemExit)
    assert not err
    assert "conda spawn" in out
