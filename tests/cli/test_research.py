from typer.testing import CliRunner
from adaptron.cli.main import app

runner = CliRunner()


def test_research_command_exists():
    result = runner.invoke(app, ["research", "--help"])
    assert result.exit_code == 0
    assert "research" in result.output.lower() or "experiment" in result.output.lower()


def test_research_missing_config(tmp_path):
    result = runner.invoke(app, ["research", "--config", str(tmp_path / "nonexistent.yaml")])
    assert result.exit_code != 0
