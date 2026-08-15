"""briefing — the one-screen decision briefing (the product's output).

Combines live + arch + quant + worth-switch into a single cached markdown
page that answers the four gauntlet questions in one read:

    上线没 / 架构改没 / 哪个量化能用 / 值不值得换

plus a one-line 信创 procurement-grade summary for a purchase memo. The m1
build ships a transparent rule-based ``WorthSwitch`` heuristic; the full
capability-close-to-frontier decision model and the enterprise signed-tarball
snapshot are planned extensions (see the stubs at the bottom).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from . import ArchDelta, DropBrief, LiveStatus, WorthSwitch
from .registry import ModelRecord

# A flat model id like "Qwen/Qwen3.8-27B" -> a filesystem-safe briefing stem.
_BRIEFING_NAME = "dropbrief-{stem}-{date}.md"


def decide_worth_switch(live: LiveStatus, arch: ArchDelta) -> WorthSwitch:
    """The m1 worth-switching heuristic — transparent, rule-based.

    The four signals:
      * ``arch_changed`` — did the structure move? (gains-from-training vs real arch)
      * ``quant_available`` — is there a runnable artifact for *some* target?
      * ``reconfig_cost`` — high if the arch moved, low if it is identical
      * ``verdict`` — skip / hold / switch, see module docstring logic
    """
    quants = [q for q in live.quant_inventory if q.live]
    quant_available = bool(quants)
    arch_changed = not arch.is_identical_arch
    reconfig_cost = "high" if arch_changed else "low"

    if not quant_available:
        verdict = "hold"
        rationale = (
            "暂无可用量化产物在线 —— 发布可能仍在进行中（页面曾被 mid-release 下架），"
            "建议等待量化上架后再评估。"
        )
    elif arch_changed:
        verdict = "switch"
        rationale = (
            f"架构相对 {arch.prior_model_id} 有 {len(arch.changed_fields)} 项变更且量化已就位 —— "
            "结构层面确有更新且可部署，值得为这波 drop 走一遍 re-config。"
        )
    else:
        verdict = "hold"
        rationale = (
            f"架构与 {arch.prior_model_id} 同构，能力增益源于训练而非结构；"
            "reconfig 成本低但架构红利为零，按业务需要灰度切换即可，不必抢跑。"
        )
    return WorthSwitch(
        verdict=verdict,
        rationale=rationale,
        arch_changed=arch_changed,
        quant_available=quant_available,
        reconfig_cost=reconfig_cost,
    )


def build_brief(
    record: ModelRecord,
    live: LiveStatus,
    arch: ArchDelta,
    family: str,
) -> DropBrief:
    """Assemble a DropBrief from its fetched + diffed parts."""
    worth = decide_worth_switch(live, arch)
    return DropBrief(
        model_id=record.model_id,
        family=family,
        live_status=live,
        arch_delta=arch,
        quant_inventory=live.quant_inventory,
        worth_switch=worth,
    )


def procurement_summary(brief: DropBrief) -> str:
    """One-line 信创 procurement-grade summary for a purchase memo."""
    ws = brief.worth_switch
    arch_clause = (
        f"架构相对 {brief.arch_delta.prior_model_id} 有 {len(brief.arch_delta.changed_fields)} 项变更"
        if ws.arch_changed
        else f"架构与 {brief.arch_delta.prior_model_id} 同构"
    )
    live_repos = [r.repo for r in brief.live_status.repos if r.live]
    surfaces = "/".join(sorted({r.surface for r in brief.live_status.repos if r.live})) or "无"
    quant_kinds = sorted({q.kind.upper() for q in brief.quant_inventory if q.live}) or ["无在线量化"]
    verdict_cn = {"switch": "建议切换", "hold": "建议持有", "skip": "暂缓"}[ws.verdict]
    return (
        f"信创建议 [{verdict_cn}]：{brief.model_id} —— {arch_clause}；"
        f"在线镜像 {surfaces}（{', '.join(live_repos) or '—'}）；"
        f"可用量化 {'/'.join(quant_kinds)}；reconfig 成本 {ws.reconfig_cost}；"
        f"依据 arch×quant×reconfig 启发式，可入采购备忘。"
    )


def render_briefing(brief: DropBrief) -> str:
    """Render the one-screen decision briefing as markdown."""
    live = brief.live_status
    arch = brief.arch_delta
    ws = brief.worth_switch
    fetched = brief.fetched_at.strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = []
    lines.append(f"# dropbrief 简报 — {brief.model_id}")
    lines.append("")
    lines.append(f"> 家族 **{brief.family}** · 抓取于 {fetched} · 缓存来源 {'命中 15min 缓存' if live.cache_hit else '实时抓取'}")
    lines.append("")
    lines.append(f"> {procurement_summary(brief)}")
    lines.append("")

    # 1. 上线没
    lines.append("## 1. 上线没")
    if not live.repos:
        lines.append("- 未探测到任何镜像源。")
    for r in live.repos:
        mark = "✓" if r.live else "✗"
        status = f"HTTP {r.http_status}" if r.http_status else "unreachable"
        lines.append(f"- {mark} **{r.surface}** `{r.repo}` — {status} · {r.note}")
    lines.append("")

    # 2. 架构改没
    lines.append("## 2. 架构改没")
    from .archdiff import summarize as _summarize

    lines.append(_summarize(arch))
    lines.append("")

    # 3. 哪个量化能用
    lines.append("## 3. 哪个量化能用")
    if not brief.quant_inventory:
        lines.append("- 注册表未声明量化产物；按需手动核查 HF/ModelScope。")
    for q in brief.quant_inventory:
        mark = "✓" if q.live else "✗"
        lines.append(f"- {mark} **{q.kind.upper()}** · {q.surface} `{q.repo}`")
    lines.append("")

    # 4. 值不值得换
    lines.append("## 4. 值不值得换")
    lines.append(f"- 判定：**{ws.verdict}** · reconfig 成本 {ws.reconfig_cost}")
    lines.append(f"- {ws.rationale}")
    lines.append("")
    lines.append(
        "_m1 启发式：arch_changed × quant_available × reconfig_cost；"
        "完整能力-贴近前沿决策模型见路线图 m3 扩展。_"
    )
    lines.append("")
    return "\n".join(lines)


def write_briefing(brief: DropBrief, out_dir: Path | str = ".") -> Path:
    """Write the briefing to ``dropbrief-<model>-<date>.md``; return its path."""
    stem = brief.model_id.split("/")[-1].lower().replace("/", "_")
    date = brief.fetched_at.strftime("%Y-%m-%d")
    base = Path(out_dir)
    base.mkdir(parents=True, exist_ok=True)
    out = base / _BRIEFING_NAME.format(stem=stem, date=date)
    out.write_text(render_briefing(brief), encoding="utf-8")
    return out


# --- m3 stub: planned paid extension ------------------------------------------
# The plan's m3 milestone envisions a 信创 enterprise offline snapshot: a
# signed, curated decision packet (tarball + signature) dropped onto an
# air-gapped box via 企业微信/邮件. v0.1 ships the *unsigned* snapshot
# (snapshot.save_snapshot) that `--offline` reads; the signed/curated
# procurement packet is the paid commercial extension and is intentionally a
# stub here.
def enterprise_signed_snapshot(_brief: DropBrief) -> Path:  # pragma: no cover - m3 stub
    """m3 stub — planned: emit a signed tarball for 信创 procurement air-gap.

    v0.1 ships the unsigned JSON snapshot (`dropbrief brief --offline` reads
    it). The signed/curated procurement-grade packet is a planned paid
    extension; not implemented in v0.1.
    """
    raise NotImplementedError("m3 stub: enterprise signed procurement snapshot is a paid extension")


def enterprise_worth_switch_model(_brief: DropBrief) -> WorthSwitch:  # pragma: no cover - m3 stub
    """m3 stub — planned: capability-close-to-frontier decision model.

    v0.1 ships the transparent rule-based decide_worth_switch heuristic. The
    learned capability-frontier model is a planned m3 extension.
    """
    raise NotImplementedError("m3 stub: capability-frontier worth-switching model is a planned extension")


__all__ = [
    "decide_worth_switch",
    "build_brief",
    "render_briefing",
    "procurement_summary",
    "write_briefing",
    "enterprise_signed_snapshot",
    "enterprise_worth_switch_model",
]
