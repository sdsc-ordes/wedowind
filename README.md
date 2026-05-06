# wedowind

Research Data Infrastructure for the WeDoWind community.

## Contents

- [Dependency management](#dependency-management)
- [Databus sync flow](#databus-sync-flow)
- [Running the sync](#running-the-sync)
  - [Run locally — sync](#run-locally--sync)
  - [Run locally — publish one version](#run-locally--publish-one-version)
  - [Runs via GitHub Actions](#runs-via-github-actions)
- [Entrypoints (`databus_manager`)](#entrypoints-databus_manager)
- [Logs (JSON Schema)](#logs-json-schema)
- [Git LFS (catalog logs)](#git-lfs-catalog-logs)
- [Test set](#test-set)
- [Catalog](#catalog)

## Dependency management

Dependencies are managed with **uv**:

```bash
uv sync
```

## Databus sync flow

This repository uses a Databus-first workflow where OEP Databus is the source
of truth before publishing:

1. Compare discrepancies between `catalog/` and OEP Databus metadata (group,
   artifact, and version), via SPARQL.
2. Append field-level rows to the discrepancy JSONL when remote metadata
   differs from local files.
3. Pull remote metadata into `catalog/` when applying changes (not `--dry-run`;
   Databus wins).
4. Classify each catalog version as `published`, `publishings_mismatch`, or `new`
   using local **publishings** (JSONL) and remote existence checks.
5. Publish only `new` versions using `databusclient` builders (with group
   metadata from `publish_group_metadata`).
6. Append successful publishes to the publishings JSONL (`catalog/logs/publishings.jsonl` by default).

## Running the sync

### Run locally — sync

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

**Compare vs classify.** Pulling Databus metadata into `catalog/` aligns **local JSON-LD**
with the remote store; it does **not** populate `publishings.jsonl`. So you can
still see **`publishings_mismatch`**: the version exists on Databus (SPARQL) but there is
no corresponding row in local publishings—for example after publishing outside this
repo, restoring catalog from git without the logs directory, or resetting that file.
Normal steady-state automation usually keeps publishings in sync with publishes from
this pipeline.

**SHACL / validation.** This codebase does not run SHACL locally before POSTing to
`/api/register`. The register endpoint validates the payload; on failure, **`publish`**
and **`sync_catalog_with_databus`** print the HTTP response body (often SHACL errors)
to standard output under **`[publish] failed:`**.

### Run locally — publish one version

```bash
uv run python -m databus_manager.publish_group_metadata \
  --version-file catalog/group-zenodo/artifact-15471425/v1.2.0/version.jsonld
```

(Same API key env var / `--api-key` as sync.)

### Runs via GitHub Actions

[`.github/workflows/databus-publish.yml`](.github/workflows/databus-publish.yml) runs
`python -m databus_manager.sync_catalog_with_databus` with `workflow_dispatch`
inputs `dry_run` and `pull_only`, and secret `DATABUS_API_KEY`.

## Entrypoints (`databus_manager`)

| Module | Role |
|--------|------|
| [`sync_catalog_with_databus.py`](src/databus_manager/sync_catalog_with_databus.py) | Orchestration: compare/pull → classify → publish new versions → append publishings. |
| [`publish_group_metadata.py`](src/databus_manager/publish_group_metadata.py) | Publish **one** `version.jsonld` with explicit group metadata (`create_dataset` + POST to OEP `/api/register`). |
| [`compare_catalog_with_databus.py`](src/databus_manager/compare_catalog_with_databus.py) | Compare local catalog vs Databus and optionally write pulled metadata back into JSON-LD files. |

CLI flags are built in [`parse.py`](src/databus_manager/parse.py):

- **`build_sync_catalog_parser()`** — used by `sync_catalog_with_databus`
- **`build_publish_group_parser()`** — used by `publish_group_metadata`

Shared pieces (keep package imports stable via [`objects/__init__.py`](src/databus_manager/objects/__init__.py) where applicable):

| Module | Role |
|--------|------|
| [`scan_catalog.py`](src/databus_manager/scan_catalog.py) | Discover `v<semver>/version.jsonld` paths and resolve group / artifact metadata paths. |
| [`sparql.py`](src/databus_manager/sparql.py) | Default SPARQL endpoint and remote version existence (`ASK`). |
| [`fetch_remote.py`](src/databus_manager/fetch_remote.py) | SPARQL SELECT helpers for remote group, artifact, and version metadata. |
| [`handle_jsonld.py`](src/databus_manager/handle_jsonld.py) | Load/write JSON-LD documents and derive group / artifact URIs from a version `@id`. |
| [`objects/metadata.py`](src/databus_manager/objects/metadata.py) | Typed **Group**, **Artifact**, and **Version** metadata objects (normalize, discrepancies, apply remote). |
| [`objects/logs.py`](src/databus_manager/objects/logs.py) | Schema-backed **discrepancy** and **publishings** rows and JSONL helpers. |

## Logs (JSON Schema)

Schemas live under [`src/schemas/`](src/schemas/):

- [`discrepancy.schema.json`](src/schemas/discrepancy.schema.json) — field-level catalog vs Databus mismatches.
- [`publishing.schema.json`](src/schemas/publishing.schema.json) — successful publishes.

Default append-only JSONL paths (override with CLI flags on sync):

- [`catalog/logs/discrepancies.jsonl`](catalog/logs/discrepancies.jsonl)
- [`catalog/logs/publishings.jsonl`](catalog/logs/publishings.jsonl)

### Git LFS (catalog logs)

[`catalog/logs/*.jsonl`](catalog/logs/) is tracked with **[Git LFS](https://git-lfs.com/)** via [`.gitattributes`](.gitattributes) so large append-only logs do not bloat the main Git object database.

One-time setup per machine:

```bash
git lfs install
```

Clone/checkout then pulls real file contents when LFS is installed; without `git-lfs`, you only see small pointer stubs.

If these files were already committed as normal Git blobs before LFS, migrate history once (team coordination required) or re-add the paths after `git lfs install` so Git replaces them with LFS objects.

## Test set

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
