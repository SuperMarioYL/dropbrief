"""dropbrief — 国产大模型发布决策简报工具.

A pre-download decision briefing for each CN open-weight model drop
(Qwen / GLM / DeepSeek / Kimi). Given a drop name, dropbrief answers the
four questions a 信创/政企 operator asks *before* touching the download
gauntlet:

    1. 上线没  — is the release actually live on HuggingFace + ModelScope?
    2. 架构改没 — what changed in config.json versus the prior drop?
    3. 哪个量化能用 — which FP8 / GGUF / AWQ artifacts exist, on which repo?
    4. 值不值得换 — given the arch-delta + quant coverage + re-config cost,
                    is switching from the currently-running model worth it?

The m1 milestone ships the fetch + 15-min cache falsifier (`dropbrief status`),
the arch-delta diff (`dropbrief diff`), and the cached one-screen briefing
(`dropbrief brief`, with `--offline` for air-gapped 信创 boxes). The full
worth-switching decision model and the enterprise signed-tarball snapshot are
planned extensions (see the module-level stubs).
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

__version__ = "0.1.0"

# Cache time-to-live for fetched live status / quant listings (seconds).
# Per mvp_plan m1: a 15-minute JSON cache falsifier — "is the drop live" and
# "which quant exists" only need refreshing every 15 min, so a repeat command
# within the window is a sub-second cache hit.
CACHE_TTL_SECONDS: int = 15 * 60


def _utcnow() -> datetime:
    """tz-aware now, so snapshots round-trip without naive-datetime bugs."""
    return datetime.now(timezone.utc)


class QuantArtifact(BaseModel):
    """A single quantized release artifact (FP8 / GGUF / AWQ)."""

    kind: str = Field(description="fp8 | gguf | awq | other")
    repo: str = Field(description="HF or ModelScope repo id")
    surface: str = Field(description="huggingface | modelscope")
    files: list[str] = Field(default_factory=list, description="matching file paths, if listed")
    live: bool = Field(default=False, description="repo resolved + reachable on last fetch")


class RepoStatus(BaseModel):
    """Live-status probe for one hosting surface (HF or ModelScope)."""

    surface: str = Field(description="huggingface | modelscope")
    repo: str
    http_status: int | None = Field(default=None, description="HTTP status of the repo resolve, None if not probed")
    live: bool = Field(default=False, description="repo is reachable and resolves to a model repo")
    file_count: int | None = Field(default=None, description="files the repo lists, if available")
    note: str = Field(default="")


class LiveStatus(BaseModel):
    """Answer to 上线没 + 哪个量化能用: HF + ModelScope reachability + quant list."""

    model_id: str
    repos: list[RepoStatus] = Field(default_factory=list)
    quant_inventory: list[QuantArtifact] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=_utcnow)
    cache_hit: bool = Field(default=False, description="True if served from the 15-min cache")


class FieldDelta(BaseModel):
    """One config.json field that changed between prior and current drop."""

    field: str
    old: object | None = None
    new: object | None = None
    change: str = Field(description="added | removed | changed")


class ArchDelta(BaseModel):
    """Answer to 架构改没: config.json field-diff versus the prior drop.

    This is the residual-value primitive (analysis_report §6): a 30-line
    scraper answers live + quant; the arch-delta is what a scraper cannot,
    so it is where the moat must rest.
    """

    model_id: str
    prior_model_id: str
    changed_fields: list[FieldDelta] = Field(default_factory=list)
    unchanged_count: int = Field(default=0, description="config fields compared and identical")
    is_identical_arch: bool = Field(default=False, description="0 changed fields → gains come from training, not arch")
    computed_at: datetime = Field(default_factory=_utcnow)


class WorthSwitch(BaseModel):
    """Answer to 值不值得换: a heuristic verdict over arch × capability × cost.

    The m1 build ships a transparent rule-based verdict. The full
    capability-close-to-frontier model is a planned extension
    (see `briefing.enterprise_worth_switch_model` — m3 stub).
    """

    verdict: str = Field(description="switch | hold | skip")
    rationale: str = Field(default="")
    arch_changed: bool = False
    quant_available: bool = False
    reconfig_cost: str = Field(default="unknown", description="low | medium | high | unknown")


class DropBrief(BaseModel):
    """The cached snapshot record — the product's core primitive (plan §2)."""

    model_id: str
    family: str
    fetched_at: datetime = Field(default_factory=_utcnow)
    live_status: LiveStatus
    arch_delta: ArchDelta
    quant_inventory: list[QuantArtifact] = Field(default_factory=list)
    worth_switch: WorthSwitch


__all__ = [
    "CACHE_TTL_SECONDS",
    "QuantArtifact",
    "RepoStatus",
    "LiveStatus",
    "FieldDelta",
    "ArchDelta",
    "WorthSwitch",
    "DropBrief",
    "__version__",
]
