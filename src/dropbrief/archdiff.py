"""archdiff — config.json field-diff versus the prior drop.

This is where the residual value rests (analysis_report §6, market_forecast
§7): a 30-line scraper answers "is it live" and "which quant exists", but it
cannot answer "did the architecture change". Operators today diff config.json
by hand — see the reddit `/r/LocalLLaMA/comments/1voblcs` finding that
"Qwen3.8-27B is identical to Qwen3.6-27B ... all the capability gains come
from training improvements". This module reproduces that judgement in code.

The diff is structural (added / removed / changed keys) and deliberately
order-independent: config.json key order is not a signal. Nested dicts are
compared by dotted path so a change inside ``model_type``-level config is
surfaced, not buried.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import ArchDelta, FieldDelta

# Keys that legitimately vary per-merge (commit hash, vocab path) and would
# noise a structural arch-diff. They are excluded so "identical architecture"
# is not masked by bookkeeping churn.
_NOISE_KEYS: frozenset[str] = frozenset(
    {
        "_name_or_path",
        "transformers_version",
        "torch_dtype",
        "use_cache",
        "bos_token_id",
        "eos_token_id",
    }
)


def flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten a nested config into dotted-path -> value pairs.

    Lists are treated as scalars (a reordering is not an arch change), dicts
    recurse. ``_NOISE_KEYS`` are dropped so bookkeeping does not mask a real
    "identical architecture" verdict.
    """
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in _NOISE_KEYS:
                continue
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                out.update(flatten(v, path))
            else:
                out[path] = v
    else:
        out[prefix or "<root>"] = obj
    return out


def compute_arch_delta(
    current: dict,
    prior: dict,
    model_id: str,
    prior_model_id: str,
    computed_at: datetime | None = None,
) -> ArchDelta:
    """Compute the structural config.json diff between two drops.

    Returns an :class:`ArchDelta` with ``changed_fields`` (added / removed /
    changed) and ``is_identical_arch`` True iff no field changed — the
    "gains come from training, not architecture" verdict.
    """
    cur_flat = flatten(current)
    prior_flat = flatten(prior)
    cur_keys = set(cur_flat)
    prior_keys = set(prior_flat)

    added = sorted(cur_keys - prior_keys)
    removed = sorted(prior_keys - cur_keys)
    changed = sorted(k for k in cur_keys & prior_keys if cur_flat[k] != prior_flat[k])
    unchanged = len(cur_keys & prior_keys) - len(changed)

    fields: list[FieldDelta] = []
    for k in added:
        fields.append(FieldDelta(field=k, old=None, new=cur_flat[k], change="added"))
    for k in removed:
        fields.append(FieldDelta(field=k, old=prior_flat[k], new=None, change="removed"))
    for k in changed:
        fields.append(FieldDelta(field=k, old=prior_flat[k], new=cur_flat[k], change="changed"))

    return ArchDelta(
        model_id=model_id,
        prior_model_id=prior_model_id,
        changed_fields=fields,
        unchanged_count=unchanged,
        is_identical_arch=not fields,
        computed_at=computed_at or datetime.now(timezone.utc),
    )


def summarize(delta: ArchDelta) -> str:
    """One-paragraph human summary of the arch-delta (for the briefing)."""
    if delta.is_identical_arch:
        return (
            f"{delta.model_id} 的架构与 {delta.prior_model_id} 完全一致 "
            f"({delta.unchanged_count} 个配置字段逐一相同，0 项变更)。"
            f"版本号变了但结构没变 —— 能力增益来自训练，而非架构；"
            f"无需为架构适配重新接线，但也不指望架构层面带来新能力。"
        )
    by_kind: dict[str, list[FieldDelta]] = {"added": [], "removed": [], "changed": []}
    for f in delta.changed_fields:
        by_kind.setdefault(f.change, []).append(f)
    parts = [
        f"{delta.model_id} 相对 {delta.prior_model_id} 有 {len(delta.changed_fields)} 项架构变更 "
        f"(新增 {len(by_kind['added'])} / 移除 {len(by_kind['removed'])} / 改动 {len(by_kind['changed'])}；"
        f"未变 {delta.unchanged_count} 项)："
    ]
    for f in delta.changed_fields[:8]:
        old = _short(f.old)
        new = _short(f.new)
        verb = {"added": "新增", "removed": "移除", "changed": "改动"}[f.change]
        parts.append(f"  · {verb} {f.field}: {old} → {new}")
    if len(delta.changed_fields) > 8:
        parts.append(f"  · …还有 {len(delta.changed_fields) - 8} 项")
    return "\n".join(parts)


def _short(v: Any) -> str:
    s = repr(v)
    return s if len(s) <= 48 else s[:45] + "…"


# --- m2 stub: planned extension -------------------------------------------------
# The plan's m2 milestone calls for reproducing the reddit /comments/1voblcs
# "identical architecture" finding end-to-end (fetch prior config from the
# registry, diff, emit the one-command verdict). compute_arch_delta + summarize
# already deliver the core of that; the stub below is the *cross-source
# corroboration* layer (cite the matching reddit thread automatically) that is
# intentionally NOT implemented in v0.1.
def reproduce_reddit_finding(_delta: ArchDelta) -> str | None:  # pragma: no cover - m2 stub
    """m2 stub — planned: auto-cite the reddit thread that the delta matches.

    v0.1 ships the diff itself (`dropbrief diff`); cross-referencing the
    operator-discussion thread is a planned m2 enhancement, not yet wired.
    """
    raise NotImplementedError("m2 stub: reddit identical-architecture corroboration is a planned extension")


__all__ = ["flatten", "compute_arch_delta", "summarize", "reproduce_reddit_finding"]
