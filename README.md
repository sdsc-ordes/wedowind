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

1. check discrepancies between `catalog/` and OEP Databus metadata,
2. pull remote metadata into `catalog/` when differences exist (Databus wins),
3. classify each catalog version as `published`, `ledger_mismatch`, or `new`,
   using local ledger + remote existence checks,
4. publish only `new` versions using `databusclient` (with group metadata),
5. append successful publishes to local ledger.

## Core modules (`databus_manager`)

- [`src/databus_manager/compare_with_databus.py`](src/databus_manager/compare_with_databus.py)
  - Compare local catalog vs OEP Databus and optionally pull remote metadata.
- [`src/databus_manager/sync_catalog_with_databus.py`](src/databus_manager/sync_catalog_with_databus.py)
  - Full orchestration: compare/pull → classify with ledger → publish new.
- [`src/databus_manager/publish_with_group_metadata.py`](src/databus_manager/publish_with_group_metadata.py)
  - Publish one version with explicit group metadata (`group_title`,
    `group_abstract`, `group_description`) via `databusclient` API builders.

## Logs (JSON Schema)

Schemas live under [`src/schemas/`](src/schemas/):

- [`discrepancy.schema.json`](src/schemas/discrepancy.schema.json) — field-level catalog vs Databus mismatches.
- [`publishing.schema.json`](src/schemas/publishing.schema.json) — successful publishes.

Python types and JSONL read/write (including validation) are in
[`src/databus_manager/objects/logs.py`](src/databus_manager/objects/logs.py).
Typed group / artefact / version metadata objects live in
[`src/databus_manager/objects/metadata.py`](src/databus_manager/objects/metadata.py).
JSON-LD file parsing and version URI helpers are in
[`src/databus_manager/objects/jsonld.py`](src/databus_manager/objects/jsonld.py).
CLI flags for the sync entrypoint are defined in
[`src/databus_manager/parser.py`](src/databus_manager/parser.py).

Append-only JSONL files (default paths):

- [`catalog/.databus/discrepancies.jsonl`](catalog/.databus/discrepancies.jsonl) — one object per differing metadata field when remote ≠ local.
- [`catalog/.databus/publish_ledger.jsonl`](catalog/.databus/publish_ledger.jsonl) — one object per successful publish (`timestamp`, `entity_id`, `entity_type`).

Use `--discrepancy-log` / `--ledger` to override paths.

## Run locally

Dry run (no writes/publish):

```bash
uv run python -m databus_manager.sync_catalog_with_databus --dry-run
```

Pull only (update local catalog from Databus, no publish):

```bash
uv run python -m databus_manager.sync_catalog_with_databus --pull-only
```

Full sync + publish:

```bash
uv run python -m databus_manager.sync_catalog_with_databus
```

Use `DATABUS_API_KEY` environment variable (or `--api-key`) for publish steps.

## Catalog

Active catalog format is documented in [`catalog/README.md`](catalog/README.md).
