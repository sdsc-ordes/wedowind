# wedowind

Research Data Infrastructure for the WeDoWind community.

## Dependency management

Dependencies are managed with **uv**:

```bash
uv sync
```

## Databus-first sync flow

This repository uses a Databus-first workflow where OEP Databus is the source
of truth before publishing:

1. Compare discrepancies between `catalog/` and OEP Databus metadata (group,
   artefact, and version), via SPARQL.
2. Append field-level rows to the discrepancy JSONL when remote metadata
   differs from local files.
3. Pull remote metadata into `catalog/` when applying changes (not `--dry-run`;
   Databus wins).
4. Classify each catalog version as `published`, `ledger_mismatch`, or `new`
   using the local ledger and remote existence checks.
5. Publish only `new` versions using `databusclient` builders (with group
   metadata from `publish_group_metadata`).
6. Append successful publishes to the publishing ledger JSONL.

## Entrypoints (`databus_manager`)

| Module | Role |
|--------|------|
| [`sync_catalog_with_databus.py`](src/databus_manager/sync_catalog_with_databus.py) | Orchestration: compare/pull → classify → publish new versions → ledger. |
| [`publish_group_metadata.py`](src/databus_manager/publish_group_metadata.py) | Publish **one** `version.jsonld` with explicit group metadata (`create_dataset` + POST to OEP `/api/register`). |
| [`compare_catalog_with_databus.py`](src/databus_manager/compare_catalog_with_databus.py) | Compare local catalog vs Databus and optionally write pulled metadata back into JSON-LD files. |

CLI flags are built in [`parse.py`](src/databus_manager/parse.py):

- **`build_sync_catalog_parser()`** — used by `sync_catalog_with_databus`
- **`build_publish_group_parser()`** — used by `publish_group_metadata`

Shared pieces (keep package imports stable via [`objects/__init__.py`](src/databus_manager/objects/__init__.py) where applicable):

| Module | Role |
|--------|------|
| [`scan_catalog.py`](src/databus_manager/scan_catalog.py) | Discover `version.jsonld` paths and resolve group / artefact metadata paths. |
| [`sparql.py`](src/databus_manager/sparql.py) | Default SPARQL endpoint and remote version existence (`ASK`). |
| [`fetch_remote.py`](src/databus_manager/fetch_remote.py) | SPARQL SELECT helpers for remote group, artefact, and version metadata. |
| [`handle_jsonld.py`](src/databus_manager/handle_jsonld.py) | Load/write JSON-LD documents and derive group / artefact URIs from a version `@id`. |
| [`objects/metadata.py`](src/databus_manager/objects/metadata.py) | Typed **Group**, **Artefact**, and **Version** metadata objects (normalize, discrepancies, apply remote). |
| [`objects/logs.py`](src/databus_manager/objects/logs.py) | Schema-backed **discrepancy** and **publishing** ledger rows and JSONL helpers. |

## Logs (JSON Schema)

Schemas live under [`src/schemas/`](src/schemas/):

- [`discrepancy.schema.json`](src/schemas/discrepancy.schema.json) — field-level catalog vs Databus mismatches.
- [`publishing.schema.json`](src/schemas/publishing.schema.json) — successful publishes.

Default append-only JSONL paths (override with CLI flags on sync):

- [`catalog/.databus/discrepancies.jsonl`](catalog/.databus/discrepancies.jsonl)
- [`catalog/.databus/publish_ledger.jsonl`](catalog/.databus/publish_ledger.jsonl)

## Run locally — sync

Dry run (no catalog writes, no publish):

```bash
uv run python -m databus_manager.sync_catalog_with_databus --dry-run
```

Pull only (apply remote metadata into catalog files when mismatches exist; no publish):

```bash
uv run python -m databus_manager.sync_catalog_with_databus --pull-only
```

Full sync + publish:

```bash
uv run python -m databus_manager.sync_catalog_with_databus
```

Use `DATABUS_API_KEY` or `--api-key` for publish steps.

## Run locally — publish one version

```bash
uv run python -m databus_manager.publish_group_metadata \
  --version-file catalog/group-zenodo/artefacts-1/version-3/version.jsonld
```

(Same API key env var / `--api-key` as sync.)

## Run tests

Install test dependencies first:

```bash
uv sync --all-groups
```

Pytest loads a `.env` file at the repository root (via `python-dotenv`), so
`DATABUS_API_KEY` can live there for local runs. You can still `export
DATABUS_API_KEY=...` in the shell; that overrides `.env` when set.

Run the full suite (unit + integration + OEP connectivity tests):

```bash
uv run pytest
```

Run only unit tests:

```bash
uv run pytest tests/unit
```

Run only integration tests:

```bash
uv run pytest tests/integration
```

Run only OEP connectivity tests:

```bash
uv run pytest tests/integration/test_integration_oep_connection.py
```

## Catalog

Layout and JSON-LD conventions are documented in [`catalog/README.md`](catalog/README.md).

## GitHub Actions

[`.github/workflows/databus-publish.yml`](.github/workflows/databus-publish.yml) runs
`python -m databus_manager.sync_catalog_with_databus` with `workflow_dispatch`
inputs `dry_run` and `pull_only`, and secret `DATABUS_API_KEY`.
