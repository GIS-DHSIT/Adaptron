"""Tests for CLI connect commands."""
from typer.testing import CliRunner
from adaptron.cli.main import app

runner = CliRunner()


def test_connect_list_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("ADAPTRON_CONNECTIONS_FILE", str(tmp_path / "connections.yaml"))
    result = runner.invoke(app, ["connect-list"])
    assert result.exit_code == 0
    assert "No saved" in result.output


def test_connect_list_with_profile(tmp_path, monkeypatch):
    conn_file = tmp_path / "connections.yaml"
    conn_file.write_text("profiles:\n  mydb:\n    connector_type: sqlite\n")
    monkeypatch.setenv("ADAPTRON_CONNECTIONS_FILE", str(conn_file))
    result = runner.invoke(app, ["connect-list"])
    assert result.exit_code == 0
    assert "mydb" in result.output


def test_connect_remove(tmp_path, monkeypatch):
    conn_file = tmp_path / "connections.yaml"
    conn_file.write_text("profiles:\n  mydb:\n    connector_type: sqlite\n")
    monkeypatch.setenv("ADAPTRON_CONNECTIONS_FILE", str(conn_file))
    result = runner.invoke(app, ["connect-remove", "mydb"])
    assert result.exit_code == 0
    assert "removed" in result.output.lower()
