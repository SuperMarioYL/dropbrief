"""snapshot — air-gap offline snapshot read/write.

A 信创/政企 procurement box has no egress, so it cannot browse reddit /
HuggingFace / ModelScope at drop time. The `--offline` path reads a
pre-shipped snapshot directory (a JSON DropBrief written by a connected run,
or a curated public snapshot shipped in-repo under ``snapshots/``) and emits
the identical briefing with zero network calls.

Layout
------
* User snapshots: ``~/.dropbrief/snapshots/<alias>/brief.json``
* Shipped public snapshots: ``<repo>/snapshots/<alias>/brief.json`` (the free
  funnel — e.g. the latest Qwen drop ships here so a cold first run works
  offline, per mvp_plan §3 step 5).
"""

from __future__ import annotations

import os
from pathlib import Path

from . import DropBrief

DEFAULT_SNAPSHOT_DIR = Path(os.environ.get("DROPBRIEF_SNAPSHOT_DIR", Path.home() / ".dropbrief" / "snapshots"))
# Shipped public snapshots live next to the package's docs/.. checkout. They
# are bundled into the sdist so `uvx dropbrief brief --offline` works cold.
SHIPPED_SNAPSHOT_DIR = Path(__file__).resolve().parent.parent.parent / "snapshots"


def _alias_dir(alias: str, base: Path) -> Path:
    safe = alias.lower().replace("/", "_")
    return base / safe


def save_snapshot(brief: DropBrief, alias: str, snapshot_dir: Path | str = DEFAULT_SNAPSHOT_DIR) -> Path:
    """Write a DropBrief as a snapshot JSON (the connected run's export)."""
    base = Path(snapshot_dir)
    d = _alias_dir(alias, base)
    d.mkdir(parents=True, exist_ok=True)
    out = d / "brief.json"
    out.write_text(brief.model_dump_json(indent=2), encoding="utf-8")
    return out


def load_snapshot(alias: str, snapshot_dir: Path | str | None = None) -> DropBrief:
    """Read a snapshot by alias, no network.

    Looks first in ``snapshot_dir`` (default the user dir), then falls back
    to the shipped public snapshot shipped in-repo. Raises FileNotFoundError
    if neither exists — a clear "no snapshot for this drop" message is the
    only failure mode an air-gapped operator should see.
    """
    search: list[Path] = []
    if snapshot_dir is not None:
        search.append(Path(snapshot_dir))
    search.append(DEFAULT_SNAPSHOT_DIR)
    search.append(SHIPPED_SNAPSHOT_DIR)

    for base in search:
        candidate = _alias_dir(alias, base) / "brief.json"
        if candidate.exists():
            return DropBrief.model_validate_json(candidate.read_text(encoding="utf-8"))

    raise FileNotFoundError(
        f"no offline snapshot for '{alias}'. "
        f"Run `dropbrief brief {alias}` on a connected box first, or ship a "
        f"public snapshot under snapshots/{alias}/brief.json."
    )


def available_shipped() -> list[str]:
    """List the aliases that ship with a free public snapshot in-repo."""
    if not SHIPPED_SNAPSHOT_DIR.exists():
        return []
    return sorted(p.parent.name for p in SHIPPED_SNAPSHOT_DIR.glob("*/brief.json"))


__all__ = ["save_snapshot", "load_snapshot", "available_shipped", "DEFAULT_SNAPSHOT_DIR", "SHIPPED_SNAPSHOT_DIR"]
