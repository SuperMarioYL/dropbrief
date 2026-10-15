# Changelog

## [0.3.0] - 2026-10-16

### Fixed

- The 15-min cache is no longer trusted blindly: a poisoned or schema-drifted
  cache entry now degrades to a refetch instead of crashing `dropbrief status`
  with a raw pydantic traceback, and a non-dict config-cache payload no longer
  feeds `dropbrief diff` a fabricated identical-architecture verdict
  (`src/dropbrief/fetch.py`).
- `dropbrief brief --offline` reports a corrupted or mangled snapshot
  (truncated transfer is the normal air-gap failure) as a one-line error
  naming the file, instead of a raw pydantic traceback
  (`src/dropbrief/snapshot.py`).

### Added

- `dropbrief brief --save-snapshot` writes the DropBrief JSON the offline mode
  reads, closing the documented connected-to-air-gap handoff: previously no
  CLI command could produce a snapshot, even though the loader's not-found
  message told operators to run `brief` on a connected box first.

### Changed

- Version lockstep to 0.3.0 across `VERSION`, `pyproject.toml`, `__version__`
  (which drives `--version` and the fetch `User-Agent`), and
  `web/site.json` `meta.content_version`.

## [0.2.0] - 2026-09-11

### Fixed

- `dropbrief brief <unknown-model>` no longer crashes with a raw `KeyError`
  traceback and exit 1; it now prints the same clean one-line error as
  `status`/`diff` and exits 2 (`src/dropbrief/cli.py`).
- The shipped offline snapshot now lands in the wheel: `snapshots/` is
  force-included as `dropbrief/data/snapshots` and the loader searches it, so
  the quickstart `uvx dropbrief brief --offline qwen3.8-27b` works on a clean
  install (`pyproject.toml`, `src/dropbrief/snapshot.py`).
- `fetch_config` honors the registry-declared `config_path` instead of always
  fetching `config.json`, so a drop with a non-default release config is no
  longer silently diffed against the wrong file (`src/dropbrief/fetch.py`).

### Added

- The roadmapped m2 reddit corroboration: when the arch-delta is identical,
  `dropbrief diff` and the briefing auto-cite the matching
  `/r/LocalLLaMA/comments/1voblcs` operator finding from the registry's new
  `corroboration` field (`docs/model-families.yaml`, `src/dropbrief/archdiff.py`).
- A `--version` flag on the CLI, and `web/site.json` `meta.content_version`.

### Changed

- Version lockstep to 0.2.0 across `VERSION`, `pyproject.toml`,
  `__version__`, and the fetch `User-Agent` (now derived from `__version__`).

## [0.1.0] - 2026-08-15

- Initial release: `dropbrief status` (live + quant inventory with a 15-minute
  cache), `dropbrief diff` (config.json arch-delta versus the prior drop),
  `dropbrief brief` (one-screen decision briefing) with `--offline` air-gap
  snapshot support, and the Qwen / GLM / DeepSeek / Kimi model-family registry.

[0.3.0]: https://github.com/SuperMarioYL/dropbrief/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/SuperMarioYL/dropbrief/compare/v0.1.0...v0.2.0
