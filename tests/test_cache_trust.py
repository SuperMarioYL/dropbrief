"""Tests for the cache trust boundary (m9).

The 15-min cache is a best-effort optimization the tool wrote itself; a
poisoned or schema-drifted entry (torn write, upgrade residue) must degrade
to a refetch — never crash the CLI, never feed the arch-diff a fabricated
payload.
"""

from __future__ import annotations

import httpx

from dropbrief.fetch import Cache, Fetcher
from dropbrief.registry import load_default

HF = "https://huggingface.co/api/models/"
MS = "https://www.modelscope.cn/api/v1/models/"
CFG = "https://huggingface.co/Qwen/Qwen3.8-27B/resolve/main/config.json"


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url.startswith(HF):
        return httpx.Response(
            200, json={"id": "x", "siblings": [{"rfilename": "config.json"}]}
        )
    if url.startswith(MS):
        return httpx.Response(200, json={"Data": {"Files": [{"Name": "config.json"}]}})
    if url == CFG:
        return httpx.Response(200, json={"model_type": "qwen3", "hidden_size": 5120})
    return httpx.Response(404, text="no route")


def _fetcher(tmp_path) -> Fetcher:
    client = httpx.Client(
        transport=httpx.MockTransport(_handler), headers={"User-Agent": "test"}
    )
    return Fetcher(client=client, cache=Cache(tmp_path / "cache"))


def test_poisoned_live_cache_degrades_to_refetch(tmp_path):
    record = load_default().resolve("qwen3.8-27b")
    fetcher = _fetcher(tmp_path)
    fetcher._cache.set(
        f"live:{record.model_id}",
        {"model_id": record.model_id, "repos": "not-a-list"},
    )
    status = fetcher.fetch_live_status(record)
    assert status.cache_hit is False
    assert isinstance(status.repos, list)


def test_refetch_overwrites_the_poisoned_entry(tmp_path):
    record = load_default().resolve("qwen3.8-27b")
    fetcher = _fetcher(tmp_path)
    fetcher._cache.set(
        f"live:{record.model_id}",
        {"model_id": record.model_id, "repos": "not-a-list"},
    )
    fetcher.fetch_live_status(record)
    again = fetcher.fetch_live_status(record)
    assert again.cache_hit is True
    assert isinstance(again.repos, list)


def test_non_dict_live_cache_degrades_to_refetch(tmp_path):
    record = load_default().resolve("qwen3.8-27b")
    fetcher = _fetcher(tmp_path)
    fetcher._cache.set(f"live:{record.model_id}", "garbage")
    status = fetcher.fetch_live_status(record)
    assert status.cache_hit is False


def test_poisoned_config_cache_degrades_to_refetch(tmp_path):
    record = load_default().resolve("qwen3.8-27b")
    fetcher = _fetcher(tmp_path)
    fetcher._cache.set(f"config:{record.model_id}:config.json", [1, 2, 3])
    cfg = fetcher.fetch_config(record)
    assert cfg == {"model_type": "qwen3", "hidden_size": 5120}


def test_valid_live_cache_still_hits(tmp_path):
    record = load_default().resolve("qwen3.8-27b")
    fetcher = _fetcher(tmp_path)
    fetcher.fetch_live_status(record)
    assert fetcher.fetch_live_status(record).cache_hit is True


def test_valid_config_cache_still_hits(tmp_path):
    record = load_default().resolve("qwen3.8-27b")
    fetcher = _fetcher(tmp_path)
    fetcher.fetch_config(record)
    assert fetcher.fetch_config(record) == {"model_type": "qwen3", "hidden_size": 5120}
