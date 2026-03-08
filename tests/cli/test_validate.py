from typer.testing import CliRunner
from adaptron.cli.main import app

runner = CliRunner()

def test_validate_command_exists():
    result = runner.invoke(app, ["validate", "--help"])
    assert result.exit_code == 0
    assert "validate" in result.output.lower() or "model" in result.output.lower()

def test_validate_missing_model(tmp_path):
    result = runner.invoke(app, ["validate", "--model", str(tmp_path / "nonexistent")])
    assert result.exit_code != 0
