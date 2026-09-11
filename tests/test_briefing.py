"""Tests for dropbrief.briefing — the one-screen decision briefing emitter."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from dropbrief import ArchDelta, DropBrief, LiveStatus, QuantArtifact, RepoStatus, WorthSwitch
from dropbrief.briefing import (
    build_brief,
    decide_worth_switch,
    enterprise_signed_snapshot,
    enterprise_worth_switch_model,
    procurement_summary,
    render_briefing,
    write_briefing,
)
from dropbrief.registry import load_default
from dropbrief.snapshot import load_snapshot, save_snapshot


def _live(quants_live: bool, repos_live: bool = True) -> LiveStatus:
    return LiveStatus(
        model_id="Qwen/Qwen3.8-27B",
        repos=[
            RepoStatus(surface="huggingface", repo="Qwen/Qwen3.8-27B", http_status=200 if repos_live else 404,
                       live=repos_live, note="ok"),
            RepoStatus(surface="modelscope", repo="Qwen/Qwen3.8-27B", http_status=200 if repos_live else 404,
                       live=repos_live, note="ok"),
        ],
        quant_inventory=[
            QuantArtifact(kind="fp8", repo="Qwen/Qwen3.8-27B-FP8", surface="huggingface", live=quants_live),
        ] if quants_live else [],
    )


def _delta(identical: bool) -> ArchDelta:
    if identical:
        return ArchDelta(model_id="Qwen/Qwen3.8-27B", prior_model_id="Qwen/Qwen3.6-27B",
                         changed_fields=[], unchanged_count=9, is_identical_arch=True)
    from dropbrief import FieldDelta

    return ArchDelta(
        model_id="Qwen/Qwen3.8-27B",
        prior_model_id="Qwen/Qwen3.6-27B",
        changed_fields=[FieldDelta(field="hidden_size", old=5120, new=6144, change="changed")],
        unchanged_count=8,
        is_identical_arch=False,
    )


def test_worth_switch_identical_arch_with_quant_is_hold():
    ws = decide_worth_switch(_live(quants_live=True), _delta(identical=True))
    assert ws.verdict == "hold"
    assert ws.arch_changed is False
    assert ws.quant_available is True
    assert ws.reconfig_cost == "low"


def test_worth_switch_changed_arch_with_quant_is_switch():
    ws = decide_worth_switch(_live(quants_live=True), _delta(identical=False))
    assert ws.verdict == "switch"
    assert ws.arch_changed is True
    assert ws.reconfig_cost == "high"


def test_worth_switch_no_quant_is_hold():
    ws = decide_worth_switch(_live(quants_live=False), _delta(identical=False))
    assert ws.verdict == "hold"
    assert ws.quant_available is False


def test_render_briefing_has_four_sections_and_verdict():
    brief = build_brief(
        load_default().resolve("qwen3.8-27b"),
        _live(quants_live=True),
        _delta(identical=True),
        family="qwen3",
    )
    md = render_briefing(brief)
    for heading in ("1. 上线没", "2. 架构改没", "3. 哪个量化能用", "4. 值不值得换"):
        assert heading in md
    assert "信创建议" in md
    assert "hold" in md or "持有" in md
    assert "Qwen/Qwen3.8-27B" in md


def test_render_briefing_embeds_reddit_citation_for_identical_arch():
    brief = build_brief(
        load_default().resolve("qwen3.8-27b"),
        _live(quants_live=True),
        _delta(identical=True),
        family="qwen3",
    )
    md = render_briefing(brief)
    assert "1voblcs" in md


def test_render_briefing_has_no_citation_for_changed_arch():
    brief = build_brief(
        load_default().resolve("qwen3.8-27b"),
        _live(quants_live=True),
        _delta(identical=False),
        family="qwen3",
    )
    md = render_briefing(brief)
    assert "1voblcs" not in md


def test_procurement_summary_is_one_line():
    brief = build_brief(
        load_default().resolve("qwen3.8-27b"),
        _live(quants_live=True),
        _delta(identical=False),
        family="qwen3",
    )
    line = procurement_summary(brief)
    assert line.startswith("信创建议 [建议切换]")
    assert brief.model_id in line
    assert "reconfig" in line


def test_write_briefing_creates_dated_file(tmp_path):
    brief = build_brief(
        load_default().resolve("qwen3.8-27b"),
        _live(quants_live=True),
        _delta(identical=True),
        family="qwen3",
    )
    brief = brief.model_copy(update={"fetched_at": datetime(2026, 8, 16, tzinfo=timezone.utc)})
    path = write_briefing(brief, out_dir=tmp_path)
    assert path.name == "dropbrief-qwen3.8-27b-2026-08-16.md"
    assert path.exists()
    assert "dropbrief 简报" in path.read_text(encoding="utf-8")


def test_offline_snapshot_round_trip(tmp_path):
    brief = build_brief(
        load_default().resolve("qwen3.8-27b"),
        _live(quants_live=True),
        _delta(identical=True),
        family="qwen3",
    )
    save_snapshot(brief, alias="qwen3.8-27b", snapshot_dir=tmp_path)
    loaded = load_snapshot("qwen3.8-27b", snapshot_dir=tmp_path)
    assert loaded.model_id == brief.model_id
    assert loaded.worth_switch.verdict == brief.worth_switch.verdict
    assert loaded.arch_delta.is_identical_arch is True


def test_shipped_snapshot_loads_cold():
    # The free public snapshot ships in-repo; a cold `--offline` run must work.
    loaded = load_snapshot("qwen3.8-27b")
    assert loaded.model_id == "Qwen/Qwen3.8-27B"
    assert loaded.arch_delta.is_identical_arch is True
    assert loaded.worth_switch.verdict == "hold"


def test_m3_stubs_raise():
    brief = build_brief(
        load_default().resolve("qwen3.8-27b"),
        _live(quants_live=True),
        _delta(identical=True),
        family="qwen3",
    )
    with pytest.raises(NotImplementedError):
        enterprise_signed_snapshot(brief)
    with pytest.raises(NotImplementedError):
        enterprise_worth_switch_model(brief)
