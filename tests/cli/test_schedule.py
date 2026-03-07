from typer.testing import CliRunner
from adaptron.cli.main import app

runner = CliRunner()


def test_schedule_list_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("ADAPTRON_SCHEDULES_FILE", str(tmp_path / "schedules.yaml"))
    result = runner.invoke(app, ["schedule-list"])
    assert result.exit_code == 0
    assert "No active" in result.output


def test_schedule_run(tmp_path, monkeypatch):
    monkeypatch.setenv("ADAPTRON_SCHEDULES_FILE", str(tmp_path / "schedules.yaml"))
    result = runner.invoke(app, ["schedule-run", "fake-id"])
    assert result.exit_code == 0
