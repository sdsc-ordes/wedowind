# Tests

Pytest configuration lives in [`pyproject.toml`](../pyproject.toml) (`testpaths = ["tests"]`, files matching `test_*.py`).

## Commands

| Command | What runs |
|--------|------------|
| `uv run pytest` | Full suite under `tests/` |
| `uv run pytest tests/test_mappers/` | Mapper packages only (`mappers.*`) |
| `uv run pytest tests/databus_local_manager/` | Local catalog publisher (`databus_local_manager`) |
| `uv run pytest tests/databus_local_manager/unit/` | Fast unit tests only |
| `uv run pytest tests/databus_local_manager/integration/` | Integration tests (may need env/fixtures) |
| `uv run pytest path/to/test_file.py` | Single file |
| `uv run pytest -k "keyword"` | Tests whose name contains `keyword` |

Use `uv sync --all-groups` (or `uv sync --group dev`) so `pytest` is available.

## Layout

| Directory | Role |
|-----------|------|
| [`test_mappers/`](test_mappers/) | [`mappers.zenodo`](../src/mappers/zenodo/), [`mappers.ckan`](../src/mappers/ckan/), shared [`mappers.utils`](../src/mappers/utils.py). Fully mocked; no live Zenodo/CKAN calls in these files. |
| [`databus_local_manager/unit/`](databus_local_manager/unit/) | Unit tests for [`databus_local_manager`](../src/databus_local_manager/) (parse, logs, scan, sync helpers, etc.). |
| [`databus_local_manager/integration/`](databus_local_manager/integration/) | Heavier checks (e.g. live OEP register ping when `DATABUS_API_KEY` is set; catalog workflows). Some tests expect a `sample_catalog` pytest fixture — define it in a `conftest.py` if you run those tests. |

## `test_mappers/` files

| File | Covers |
|------|--------|
| `test_zenodo_mapper.py` | Zenodo → Databus mapping, timestamps, source config loading, page-size clamping for `/api/records`. |
| `test_zenodo_publish_sources.py` | [`mappers.zenodo.publish_sources`](../src/mappers/zenodo/publish_sources.py) dry-run path (mocked API + register). |
| `test_ckan_mapper.py` | CKAN → Databus mapping via mocked CKAN API. |
| `test_ckan_publish_sources.py` | [`mappers.ckan.publish_sources`](../src/mappers/ckan/publish_sources.py) dry-run path (mocked search + register). |
| `test_utils.py` | Shared mapper utilities (e.g. Databus identifiers, truncation). |

## `databus_local_manager/` files

| File | Covers |
|------|--------|
| `unit/test_parse.py` | CLI / argument helpers for prepare and publish. |
| `unit/test_scan_catalog.py` | Discovering `catalog/groups/*.json`. |
| `unit/test_publish_group_metadata.py` | Prepare-metadata / group validation wiring. |
| `unit/test_sync_catalog_with_databus.py` | Publishing pipeline helpers vs sample catalog (needs fixture when enabled). |
| `unit/test_logs.py` | Publishings JSONL parsing and validation (`logs.py`). |
| `integration/test_integration_publish_group_metadata.py` | End-to-end prepare with catalog fixture when present. |
| `integration/test_integration_sync_catalog_with_databus.py` | Publish flow with mocks / fixture when present. |
| `integration/test_integration_oep_connection.py` | Optional live register connectivity when `DATABUS_API_KEY` is set. |
