"""Tests for dropbrief.archdiff — the arch-delta primitive (residual value)."""

from __future__ import annotations

import pytest

from dropbrief import ArchDelta, FieldDelta
from dropbrief.archdiff import compute_arch_delta, flatten, reproduce_reddit_finding, summarize


def _delta(cur: dict, prior: dict) -> ArchDelta:
    return compute_arch_delta(cur, prior, "Qwen/Qwen3.8-27B", "Qwen/Qwen3.6-27B")


def test_flatten_dotted_paths():
    flat = flatten({"a": 1, "b": {"c": 2, "d": {"e": 3}}, "_name_or_path": "x"})
    assert flat == {"a": 1, "b.c": 2, "b.d.e": 3}
    # bookkeeping keys are dropped so they don't mask an identical-arch verdict
    assert "_name_or_path" not in flat


def test_identical_configs_mean_identical_arch():
    cfg = {
        "model_type": "qwen3",
        "architectures": ["Qwen3ForCausalLM"],
        "hidden_size": 5120,
        "num_attention_heads": 40,
        "num_hidden_layers": 64,
        "num_key_value_heads": 8,
        "intermediate_size": 13824,
        "max_position_embeddings": 32768,
        "vocab_size": 152064,
        "_name_or_path": "Qwen/Qwen3.8-27B",  # noise — must not count
    }
    delta = _delta(cfg, {**cfg, "_name_or_path": "Qwen/Qwen3.6-27B"})
    assert delta.is_identical_arch is True
    assert delta.changed_fields == []
    assert delta.unchanged_count == 9


def test_detects_added_removed_changed():
    cur = {"model_type": "qwen3", "hidden_size": 5120, "new_field": 1, "rope": {"theta": 1000000}}
    prior = {
        "model_type": "qwen3",
        "hidden_size": 5120,
        "dropped_field": 9,
        "rope": {"theta": 10000},
    }
    delta = _delta(cur, prior)
    kinds = {f.field: f.change for f in delta.changed_fields}
    assert kinds == {"new_field": "added", "dropped_field": "removed", "rope.theta": "changed"}
    assert delta.is_identical_arch is False
    added = next(f for f in delta.changed_fields if f.field == "new_field")
    assert added.old is None and added.new == 1
    changed = next(f for f in delta.changed_fields if f.field == "rope.theta")
    assert changed.old == 10000 and changed.new == 1000000


def test_summarize_identical():
    delta = _delta({"a": 1}, {"a": 1})
    s = summarize(delta)
    assert "完全一致" in s
    assert "0 项变更" in s


def test_summarize_changed_lists_fields():
    delta = _delta({"a": 1}, {"a": 2})
    s = summarize(delta)
    assert "1 项架构变更" in s
    assert "a" in s


def test_reproduce_reddit_finding_is_m2_stub():
    # The cross-source corroboration layer is intentionally a planned extension.
    with pytest.raises(NotImplementedError):
        reproduce_reddit_finding(_delta({"a": 1}, {"a": 1}))
