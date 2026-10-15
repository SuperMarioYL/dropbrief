"""Tests for the dropbrief CLI surface — command contracts on bad input."""

from __future__ import annotations

from typer.testing import CliRunner

import dropbrief.snapshot as snap
from dropbrief import LiveStatus, RepoStatus
from dropbrief.cli import app
from dropbrief.snapshot import load_snapshot

runner = CliRunner()


class _StubFetcher:
    """Offline stand-in for fetch.Fetcher on the online brief path."""

    def fetch_live_status(self, record):
        return LiveStatus(
            model_id=record.model_id,
            repos=[
                RepoStatus(
                    surface="huggingface",
                    repo=record.hf_repo,
                    http_status=200,
                    live=True,
                    note="ok",
                )
            ],
        )

    def fetch_config(self, record, config_path=None):
        return {"model_type": "qwen3", "hidden_size": 5120}


def _flat(text: str) -> str:
    # rich hard-wraps long lines in captured output; rejoin them so path
    # containment checks are wrap-tolerant.
    return text.replace("\n", "")


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


def test_brief_offline_corrupt_snapshot_is_clean_error_exit_1(tmp_path, monkeypatch):
    # A snapshot mangled in air-gap transfer must produce a one-line error
    # naming the file — never a raw pydantic traceback (m10).
    alias_dir = tmp_path / "qwen3.8-27b"
    alias_dir.mkdir(parents=True)
    (alias_dir / "brief.json").write_text("{model_id: oops\n", encoding="utf-8")
    monkeypatch.setattr(snap, "DEFAULT_SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(snap, "PACKAGED_SNAPSHOT_DIR", tmp_path / "no-packaged")
    monkeypatch.setattr(snap, "SHIPPED_SNAPSHOT_DIR", tmp_path / "no-shipped")

    result = runner.invoke(app, ["brief", "qwen3.8-27b", "--offline"])
    assert result.exit_code == 1
    assert "error:" in result.output
    assert str(alias_dir / "brief.json") in _flat(result.output)
    assert "Traceback" not in result.output
    assert "ValidationError" not in result.output


def test_brief_save_snapshot_writes_the_offline_json(tmp_path, monkeypatch):
    # The connected-to-air-gap handoff: --save-snapshot writes the DropBrief
    # JSON the offline mode reads (m11).
    monkeypatch.setattr(snap, "DEFAULT_SNAPSHOT_DIR", tmp_path / "snapshots")
    monkeypatch.setattr("dropbrief.cli.Fetcher", _StubFetcher)

    result = runner.invoke(
        app, ["brief", "qwen3.8-27b", "--save-snapshot", "--out", str(tmp_path / "md")]
    )
    assert result.exit_code == 0, result.output
    snap_file = tmp_path / "snapshots" / "qwen3.8-27b" / "brief.json"
    assert snap_file.exists()
    assert str(snap_file) in _flat(result.output)

    loaded = load_snapshot("qwen3.8-27b", snapshot_dir=tmp_path / "snapshots")
    assert loaded.model_id == "Qwen/Qwen3.8-27B"
    assert loaded.arch_delta.is_identical_arch is True


def test_brief_save_snapshot_conflicts_with_offline():
    result = runner.invoke(app, ["brief", "--offline", "--save-snapshot", "qwen3.8-27b"])
    assert result.exit_code == 2
    assert "error:" in result.output
    assert "--save-snapshot" in result.output
    assert "Traceback" not in result.output
