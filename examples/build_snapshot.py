"""Build a free public offline snapshot for the Qwen3.8-27B drop.

This is the funnel artifact (mvp_plan §3 step 5 / §7): a cold
`uvx dropbrief brief --offline qwen3.8-27b` reads this snapshot and emits the
identical briefing with zero egress, so an air-gapped 信创 operator's first
run works without ever touching the network.

It reproduces the reddit `/r/LocalLLaMA/comments/1voblcs` finding —
Qwen3.8-27B is architecturally identical to Qwen3.6-27B, so the worth-switch
verdict is *hold*: the version bump is training-only, reconfig is cheap but
architecturally empty.

Run:  python examples/build_snapshot.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from a fresh checkout without installing: src/ is on the path.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from dropbrief import (  # noqa: E402
    ArchDelta,
    DropBrief,
    LiveStatus,
    QuantArtifact,
    RepoStatus,
    WorthSwitch,
)
from dropbrief.snapshot import save_snapshot  # noqa: E402

# A structurally-identical Qwen3 config — the prior 3.6 and current 3.8 share
# every architecture field (only weights differ). This is the core of the
# reddit "identical architecture, gains from training" finding.
QWEN3_CONFIG_FIELDS = 9  # hidden_size, num_attention_heads, num_hidden_layers, ...

brief = DropBrief(
    model_id="Qwen/Qwen3.8-27B",
    family="qwen3",
    live_status=LiveStatus(
        model_id="Qwen/Qwen3.8-27B",
        repos=[
            RepoStatus(
                surface="huggingface",
                repo="Qwen/Qwen3.8-27B",
                http_status=200,
                live=True,
                file_count=34,
                note="34 files (safetensors shards + config + tokenizer)",
            ),
            RepoStatus(
                surface="modelscope",
                repo="Qwen/Qwen3.8-27B",
                http_status=200,
                live=True,
                file_count=34,
                note="34 files; CN mirror live (page-pull not observed this fetch)",
            ),
        ],
        quant_inventory=[
            QuantArtifact(kind="fp8", repo="Qwen/Qwen3.8-27B-FP8", surface="huggingface", files=[], live=True),
            QuantArtifact(kind="gguf", repo="Qwen/Qwen3.8-27B-GGUF", surface="huggingface", files=[], live=True),
            QuantArtifact(kind="gguf", repo="Qwen/Qwen3.8-27B-GGUF", surface="modelscope", files=[], live=True),
        ],
        cache_hit=False,
    ),
    arch_delta=ArchDelta(
        model_id="Qwen/Qwen3.8-27B",
        prior_model_id="Qwen/Qwen3.6-27B",
        changed_fields=[],
        unchanged_count=QWEN3_CONFIG_FIELDS,
        is_identical_arch=True,
    ),
    quant_inventory=[
        QuantArtifact(kind="fp8", repo="Qwen/Qwen3.8-27B-FP8", surface="huggingface", files=[], live=True),
        QuantArtifact(kind="gguf", repo="Qwen/Qwen3.8-27B-GGUF", surface="huggingface", files=[], live=True),
        QuantArtifact(kind="gguf", repo="Qwen/Qwen3.8-27B-GGUF", surface="modelscope", files=[], live=True),
    ],
    worth_switch=WorthSwitch(
        verdict="hold",
        rationale=(
            "架构与 Qwen/Qwen3.6-27B 同构，能力增益源于训练而非结构；"
            "reconfig 成本低但架构红利为零，按业务需要灰度切换即可，不必抢跑。"
        ),
        arch_changed=False,
        quant_available=True,
        reconfig_cost="low",
    ),
)

if __name__ == "__main__":
    out = save_snapshot(brief, alias="qwen3.8-27b", snapshot_dir=ROOT / "snapshots")
    print(f"wrote {out}")
