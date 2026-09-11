# Changelog

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
