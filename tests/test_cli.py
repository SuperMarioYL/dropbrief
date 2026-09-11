"""Tests for the dropbrief CLI surface — command contracts on bad input."""

from __future__ import annotations

from typer.testing import CliRunner

from dropbrief.cli import app

runner = CliRunner()


def test_brief_unknown_model_is_clean_error_exit_2():
    result = runner.invoke(app, ["brief", "not-a-model"])
    assert result.exit_code == 2
    assert "error:" in result.output
    assert "unknown model" in result.output
    assert "Traceback" not in result.output
    assert "KeyError" not in result.output


def test_brief_offline_unknown_model_is_clean_error_exit_2():
    result = runner.invoke(app, ["brief", "--offline", "not-a-model"])
    assert result.exit_code == 2
    assert "error:" in result.output
    assert "unknown model" in result.output
    assert "Traceback" not in result.output


def test_status_unknown_model_stays_exit_2():
    result = runner.invoke(app, ["status", "not-a-model"])
    assert result.exit_code == 2
    assert "unknown model" in result.output


def test_diff_unknown_model_stays_exit_2():
    result = runner.invoke(app, ["diff", "not-a-model"])
    assert result.exit_code == 2
    assert "unknown model" in result.output
