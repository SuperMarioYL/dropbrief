"""Tests for dropbrief.fetch — the m1 fetch + 15-min cache falsifier.

All network is stubbed via ``httpx.MockTransport``; no real egress.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from dropbrief.fetch import Cache, Fetcher
from dropbrief.registry import load_default

HF = "https://huggingface.co/api/models/"
MS = "https://www.modelscope.cn/api/v1/models/"
CFG = "https://huggingface.co/"


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url.startswith(HF):
        repo = url[len(HF):]
        if "pulled" in repo:
            return httpx.Response(404, json={"error": "repo not found"})
        return httpx.Response(
            200,
            json={
                "id": repo,
                "siblings": [
                    {"rfilename": "config.json"},
                    {"rfilename": "model.safetensors"},
                    {"rfilename": "tokenizer.json"},
                ],
            },
        )
    if url.startswith(MS):
        repo = url[len(MS):]
        return httpx.Response(
            200,
            json={"Data": {"Files": [{"Name": "config.json"}, {"Name": "model.pt"}]}},
        )
    if url.startswith(CFG) and url.endswith("config.json"):
        return httpx.Response(200, json={"model_type": "qwen3", "hidden_size": 5120})
    return httpx.Response(404, text="no route")


def _client() -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(_handler), headers={"User-Agent": "test"})


def _fetcher(tmp_path: Path) -> Fetcher:
    return Fetcher(client=_client(), cache=Cache(tmp_path / "cache"))


def test_resolve_known_drops():
    reg = load_default()
    for name in ("qwen3.8-27b", "Qwen3.8-27B", "Qwen/Qwen3.8-27B"):
        rec = reg.resolve(name)
        assert rec.model_id == "Qwen/Qwen3.8-27B"
    assert reg.resolve("glm-4.5").model_id == "THUDM/GLM-4.5"


def test_resolve_unknown_raises():
    reg = load_default()
    with pytest.raises(KeyError):
        reg.resolve("llama-3")


def test_fetch_live_status_parses_both_surfaces(tmp_path):
    rec = load_default().resolve("qwen3.8-27b")
    live = _fetcher(tmp_path).fetch_live_status(rec)
    surfaces = {r.surface for r in live.repos}
    assert surfaces == {"huggingface", "modelscope"}
    assert all(r.live for r in live.repos)
    assert live.repos[0].file_count == 3  # HF siblings
    assert live.repos[1].file_count == 2  # MS Files
    # quant inventory mirrors the registry specs, probed live
    kinds = sorted(q.kind for q in live.quant_inventory)
    assert kinds == ["fp8", "gguf", "gguf"]
    assert all(q.live for q in live.quant_inventory)


def test_fetch_live_status_15min_cache_hit(tmp_path):
    rec = load_default().resolve("qwen3.8-27b")
    fetcher = _fetcher(tmp_path)
    first = fetcher.fetch_live_status(rec)
    assert first.cache_hit is False
    second = fetcher.fetch_live_status(rec)
    assert second.cache_hit is True
    # identical content served from cache
    assert second.model_id == first.model_id
    assert [r.live for r in second.repos] == [r.live for r in first.repos]


def test_cache_expires_after_ttl(tmp_path):
    cache = Cache(tmp_path / "c", ttl_seconds=1)
    cache.set("k", {"v": 1}, fetched_at=datetime.now(timezone.utc))
    assert cache.get("k") == {"v": 1}
    expired = datetime.now(timezone.utc) - timedelta(seconds=60)
    cache.set("k2", {"v": 2}, fetched_at=expired)
    assert cache.get("k2") is None


def test_pulled_repo_marked_not_live(tmp_path):
    rec = load_default().resolve("qwen3.8-27b")
    rec = rec.model_copy(update={"hf_repo": "Qwen/pulled-mid-release"})
    live = _fetcher(tmp_path).fetch_live_status(rec)
    hf = next(r for r in live.repos if r.surface == "huggingface")
    assert hf.live is False
    assert hf.http_status == 404


def test_fetch_config_returns_parsed_json(tmp_path):
    rec = load_default().resolve("qwen3.8-27b")
    cfg = _fetcher(tmp_path).fetch_config(rec)
    assert cfg == {"model_type": "qwen3", "hidden_size": 5120}


def test_fetch_config_uses_registry_config_path(tmp_path):
    # The registry's config_path is the single source of truth; a drop that
    # declares a non-default release config must be fetched from that path,
    # not the hardcoded default config.json.
    rec = load_default().resolve("qwen3.8-27b").model_copy(
        update={"config_path": "config_v2.json"}
    )
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        seen.append(url)
        if url.endswith("config_v2.json"):
            return httpx.Response(200, json={"model_type": "v2-arch", "hidden_size": 9999})
        if url.endswith("config.json"):
            return httpx.Response(200, json={"model_type": "WRONG-DEFAULT-CONFIG"})
        return httpx.Response(404, text="no route")

    client = httpx.Client(transport=httpx.MockTransport(handler), headers={"User-Agent": "test"})
    fetcher = Fetcher(client=client, cache=Cache(tmp_path / "cache"))

    cfg = fetcher.fetch_config(rec)
    assert cfg == {"model_type": "v2-arch", "hidden_size": 9999}
    assert any(u.endswith("config_v2.json") for u in seen)
    assert not any(u.endswith("/config.json") for u in seen)

    # repeat call is served from the per-path cache — still one request
    fetcher.fetch_config(rec)
    assert len(seen) == 1


def test_fetch_config_cached(tmp_path):
    rec = load_default().resolve("qwen3.8-27b")
    fetcher = _fetcher(tmp_path)
    calls = {"n": 0}
    orig = fetcher.client.get

    def counting_get(url, *a, **kw):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        return orig(url, *a, **kw)

    fetcher.client.get = counting_get  # type: ignore[assignment]
    fetcher.fetch_config(rec)
    fetcher.fetch_config(rec)
    # second call served from cache — only one network GET
    assert calls["n"] == 1
