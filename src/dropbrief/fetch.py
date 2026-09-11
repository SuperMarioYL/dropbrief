"""fetch — the m1 fetch + 15-min cache falsifier.

This module IS the killer-falsifier from analysis_report §6: "build a 30-line
scraper; if it answers live/arch/quant/worth-switching for the next drop, the
moat is gone and only the arch-delta + worth-switching intelligence remains."

It deliberately stays small and transparent. The residual value lives in
:mod:`dropbrief.archdiff` and :mod:`dropbrief.briefing`, not here.

Design notes
------------
* An ``httpx.Client`` is injected (or constructed lazily) so the test suite can
  drive the falsifier with an ``httpx.MockTransport`` — no real network, no
  flakiness, no need for recorded cassettes.
* The 15-minute JSON cache (plan m1) lives on disk under
  ``~/.dropbrief/cache/`` so a repeat ``dropbrief status`` within the window is
  a sub-second cache hit — the whole point of "one cached command".
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from . import CACHE_TTL_SECONDS, __version__
from . import LiveStatus, QuantArtifact, RepoStatus
from .registry import ModelRecord

HUGGINGFACE_API = "https://huggingface.co/api/models/{repo}"
HUGGINGFACE_CONFIG = "https://huggingface.co/{repo}/resolve/main/{path}"
MODELSCOPE_API = "https://www.modelscope.cn/api/v1/models/{repo}"
# A short, honest User-Agent. HF/ModelScope both 403 a bare httpx UA.
# Derived from __version__ so the UA tracks the lockstep version.
USER_AGENT = f"dropbrief/{__version__} (+https://github.com/SuperMarioYL/dropbrief)"

DEFAULT_CACHE_DIR = Path(os.environ.get("DROPBRIEF_CACHE_DIR", Path.home() / ".dropbrief" / "cache"))


class Cache:
    """A tiny on-disk JSON cache with a TTL — the 15-min falsifier cache."""

    def __init__(self, cache_dir: Path | str = DEFAULT_CACHE_DIR, ttl_seconds: int = CACHE_TTL_SECONDS) -> None:
        self.dir = Path(cache_dir)
        self.ttl = timedelta(seconds=ttl_seconds)

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.dir / f"{digest}.json"

    def get(self, key: str) -> dict | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        ts = payload.get("fetched_at")
        if not ts:
            return None
        try:
            fetched = datetime.fromisoformat(ts)
        except ValueError:
            return None
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - fetched > self.ttl:
            return None
        return payload.get("data")

    def set(self, key: str, data: dict, fetched_at: datetime | None = None) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        ts = (fetched_at or datetime.now(timezone.utc)).isoformat()
        self._path(key).write_text(
            json.dumps({"fetched_at": ts, "data": data}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def clear(self) -> None:
        for p in self.dir.glob("*.json"):
            try:
                p.unlink()
            except OSError:
                pass


class Fetcher:
    """Fetches live status + quant inventory + config.json for a drop."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        cache: Cache | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._client = client
        self._cache = cache or Cache()
        self._timeout = timeout

    @property
    def client(self) -> httpx.Client:
        # Lazily build a real client only when one was not injected (i.e. in
        # production; tests always inject one with a MockTransport).
        if self._client is None:
            self._client = httpx.Client(
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
                timeout=self._timeout,
            )
        return self._client

    # -- public API ---------------------------------------------------------

    def fetch_live_status(self, record: ModelRecord) -> LiveStatus:
        """Probe HF + ModelScope for the drop + its registered quant repos.

        Result is the cached LiveStatus; ``cache_hit`` is True when served
        from the 15-min cache without any network call.
        """
        cache_key = f"live:{record.model_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return LiveStatus.model_validate(cached).model_copy(update={"cache_hit": True})

        repos = [self._probe_hf(record.hf_repo), self._probe_modelscope(record.modelscope_id)]
        quants = self._fetch_quant_inventory(record)
        status = LiveStatus(
            model_id=record.model_id,
            repos=repos,
            quant_inventory=quants,
        )
        self._cache.set(cache_key, status.model_dump(mode="json"))
        return status

    def fetch_quant_inventory(self, record: ModelRecord) -> list[QuantArtifact]:
        """Public wrapper used by the CLI's quant-only view."""
        return self._fetch_quant_inventory(record)

    def fetch_config(self, record: ModelRecord, config_path: str | None = None) -> dict:
        """Fetch the release ``config.json`` from HuggingFace for arch-diff.

        Cached per (model_id, path) under the same 15-min cache. The path
        defaults to the registry-declared ``record.config_path`` (the single
        source of truth); the explicit argument stays an override.
        """
        path = config_path or record.config_path
        cache_key = f"config:{record.model_id}:{path}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        url = HUGGINGFACE_CONFIG.format(repo=record.hf_repo, path=path)
        data = self._get_json_or_raise(url, expect_kind=dict)
        self._cache.set(cache_key, data)
        return data

    # -- internals ----------------------------------------------------------

    def _fetch_quant_inventory(self, record: ModelRecord) -> list[QuantArtifact]:
        out: list[QuantArtifact] = []
        for spec in record.quants:
            if spec.surface == "modelscope":
                repo_status = self._probe_modelscope(spec.repo)
            else:
                repo_status = self._probe_hf(spec.repo)
            out.append(
                QuantArtifact(
                    kind=spec.kind,
                    repo=spec.repo,
                    surface=spec.surface,
                    files=[],
                    live=repo_status.live,
                )
            )
        return out

    def _probe_hf(self, repo: str) -> RepoStatus:
        url = HUGGINGFACE_API.format(repo=repo)
        try:
            resp = self.client.get(url)
        except httpx.HTTPError as exc:
            return RepoStatus(surface="huggingface", repo=repo, http_status=None, live=False, note=f"error: {exc}")
        if resp.status_code != 200:
            return RepoStatus(
                surface="huggingface", repo=repo, http_status=resp.status_code, live=False, note="not found / pulled"
            )
        try:
            body = resp.json()
        except ValueError:
            body = {}
        siblings = body.get("siblings") or []
        files = [s.get("rfilename") for s in siblings if isinstance(s, dict) and s.get("rfilename")]
        return RepoStatus(
            surface="huggingface",
            repo=repo,
            http_status=200,
            live=True,
            file_count=len(files),
            note=f"{len(files)} files" if files else "live, no file list",
        )

    def _probe_modelscope(self, repo: str) -> RepoStatus:
        url = MODELSCOPE_API.format(repo=repo)
        try:
            resp = self.client.get(url)
        except httpx.HTTPError as exc:
            return RepoStatus(surface="modelscope", repo=repo, http_status=None, live=False, note=f"error: {exc}")
        if resp.status_code != 200:
            return RepoStatus(
                surface="modelscope", repo=repo, http_status=resp.status_code, live=False, note="not found / pulled"
            )
        try:
            body = resp.json()
        except ValueError:
            body = {}
        # ModelScope wraps payload in {"Data": {"Files": [{"Name": ...}]}}
        data = body.get("Data") if isinstance(body, dict) else None
        files = []
        if isinstance(data, dict):
            raw_files = data.get("Files") or []
            files = [f.get("Name") for f in raw_files if isinstance(f, dict) and f.get("Name")]
        return RepoStatus(
            surface="modelscope",
            repo=repo,
            http_status=200,
            live=True,
            file_count=len(files),
            note=f"{len(files)} files" if files else "live, no file list",
        )

    def _get_json_or_raise(self, url: str, expect_kind: type) -> dict | list:
        resp = self.client.get(url)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, expect_kind):
            raise ValueError(f"unexpected JSON shape at {url}: {type(data).__name__}")
        return data


__all__ = ["Cache", "Fetcher", "DEFAULT_CACHE_DIR"]
