"""Tests for the wheel packaging of shipped offline snapshots (m5).

The v0.1.0 wheel shipped docs/model-families.yaml but NOT snapshots/, so
`uvx dropbrief brief --offline qwen3.8-27b` failed on a clean install.
These tests pin both halves of the fix: the hatch force-include that puts
snapshots/ into the wheel, and the loader lookup that finds them there.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import dropbrief.snapshot as snap
from dropbrief import DropBrief

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_wheel_force_includes_snapshots():
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    force_include = data["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    assert force_include.get("snapshots") == "dropbrief/data/snapshots"


def test_load_snapshot_prefers_packaged_data_dir(tmp_path, monkeypatch):
    # A marker brief placed where the wheel ships snapshots must win over the
    # source checkout's copy, proving the packaged dir is searched first.
    shipped = Path(snap.SHIPPED_SNAPSHOT_DIR) / "qwen3.8-27b" / "brief.json"
    brief = DropBrief.model_validate_json(shipped.read_text(encoding="utf-8"))
    marker = brief.model_copy(update={"model_id": "PACKAGED/marker"})

    packaged = tmp_path / "pkg" / "snapshots"
    alias_dir = packaged / "qwen3.8-27b"
    alias_dir.mkdir(parents=True)
    (alias_dir / "brief.json").write_text(marker.model_dump_json(indent=2), encoding="utf-8")

    monkeypatch.setattr(snap, "DEFAULT_SNAPSHOT_DIR", tmp_path / "no-user-snapshots")
    monkeypatch.setattr(snap, "PACKAGED_SNAPSHOT_DIR", packaged)

    loaded = snap.load_snapshot("qwen3.8-27b")
    assert loaded.model_id == "PACKAGED/marker"


def test_load_snapshot_still_falls_back_to_repo_checkout(tmp_path, monkeypatch):
    # With no packaged snapshot present, the repo checkout copy still serves.
    monkeypatch.setattr(snap, "DEFAULT_SNAPSHOT_DIR", tmp_path / "no-user-snapshots")
    monkeypatch.setattr(snap, "PACKAGED_SNAPSHOT_DIR", tmp_path / "no-packaged")

    loaded = snap.load_snapshot("qwen3.8-27b")
    assert loaded.model_id == "Qwen/Qwen3.8-27B"
    assert loaded.arch_delta.is_identical_arch is True
