# tests/cli/test_cli.py
from typer.testing import CliRunner
from adaptron.cli.main import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_init_creates_config(tmp_path):
    result = runner.invoke(app, ["init", "--project-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "adaptron.yaml").exists()
