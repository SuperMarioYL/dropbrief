"""Model-family registry — resolves a drop alias to its HF/ModelScope/prior map.

Loaded from ``docs/model-families.yaml`` (the single source of truth). The
alias normaliser is intentionally permissive: ``Qwen3.8-27B``, ``qwen3.8-27b``,
``Qwen/Qwen3.8-27B`` and ``qwen3.8-27b`` all resolve to the same record, so a
user typing a model name off a reddit thread does not have to match a canonical
spelling.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

# The registry ships two ways: bundled inside the installed wheel
# (``dropbrief/data/model-families.yaml``, force-included from docs/ at build
# time) and as the canonical repo file under docs/ for dev checkouts. We try
# the package-internal copy first (works for `uvx` with no checkout present),
# then the repo docs/ file (works for editable/clone runs).
_PKG_BUNDLED = Path(__file__).resolve().parent / "data" / "model-families.yaml"
_REPO_DOCS = Path(__file__).resolve().parent.parent.parent / "docs" / "model-families.yaml"


def _bundled_path() -> Path:
    for candidate in (_PKG_BUNDLED, _REPO_DOCS):
        if candidate.exists():
            return candidate
    # Fall through to _PKG_BUNDLED so the FileNotFoundError is informative.
    return _PKG_BUNDLED


class QuantSpec(BaseModel):
    kind: str
    repo: str
    surface: str


class Corroboration(BaseModel):
    """A community finding that corroborates an identical-arch delta (m2).

    Carried in model-families.yaml next to the drop it evidences, so the
    citation rides the same edit workflow operators already use per drop —
    offline-safe by construction, no live scrape.
    """

    url: str
    title: str
    quote: str = ""


class ModelRecord(BaseModel):
    alias: str
    model_id: str
    hf_repo: str
    modelscope_id: str
    config_path: str = "config.json"
    prior_alias: str | None = None
    quants: list[QuantSpec] = Field(default_factory=list)
    corroboration: Corroboration | None = None


class Family(BaseModel):
    family: str
    vendor: str
    homepage: str
    models: list[ModelRecord]


class Registry:
    """In-memory view over docs/model-families.yaml."""

    def __init__(self, families: list[Family]) -> None:
        self._families = families
        self._by_alias: dict[str, ModelRecord] = {}
        self._by_model_id: dict[str, ModelRecord] = {}
        self._family_of: dict[str, str] = {}
        for fam in families:
            for m in fam.models:
                self._family_of[m.model_id] = fam.family
                for key in _aliases_for(m):
                    # First registration wins, so the bundled file's order is
                    # canonical and a user shadowing it is a no-op.
                    self._by_alias.setdefault(key.lower(), m)
                self._by_model_id.setdefault(m.model_id.lower(), m)

    def families(self) -> list[Family]:
        return list(self._families)

    def resolve(self, name: str) -> ModelRecord:
        """Resolve a free-form drop name to its registry record.

        Raises KeyError with a helpful message listing known drops if the
        name does not match.
        """
        key = name.strip().lower()
        if key in self._by_alias:
            return self._by_alias[key]
        if key in self._by_model_id:
            return self._by_model_id[key]
        known = sorted({m.alias for f in self._families for m in f.models})
        raise KeyError(
            f"unknown model '{name}'. Known drops: {', '.join(known)}"
        )

    def prior(self, record: ModelRecord) -> ModelRecord | None:
        if not record.prior_alias:
            return None
        return self._by_alias.get(record.prior_alias.lower())

    def family_of(self, record: ModelRecord) -> str:
        return self._family_of.get(record.model_id, record.model_id.split("/")[0].lower())


def _aliases_for(m: ModelRecord) -> list[str]:
    """Every spelling a user might type for this drop."""
    keys = [m.alias, m.model_id, m.hf_repo, m.modelscope_id]
    # Also accept the bare repo suffix (e.g. "Qwen3.8-27B" from "Qwen/Qwen3.8-27B").
    for repo in (m.hf_repo, m.modelscope_id):
        if "/" in repo:
            keys.append(repo.split("/", 1)[1])
    return keys


@lru_cache(maxsize=1)
def load_default() -> Registry:
    """Load the registry bundled with the package (docs/model-families.yaml)."""
    return load(_bundled_path())


def load(path: Path | str) -> Registry:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    families = [Family.model_validate(f) for f in data["families"]]
    return Registry(families)


__all__ = ["Registry", "Family", "ModelRecord", "QuantSpec", "Corroboration", "load", "load_default"]
