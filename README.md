# wedowind

Research Data Infrastructure for the WeDoWind community.

## Contents

- [wedowind](#wedowind)
  - [Contents](#contents)
  - [Setup](#setup)
  - [Monthly action or manual run](#monthly-action-or-manual-run)
  - [Publish Commands](#publish-commands)
    - [1a) Zenodo mapper publish (synced sources)](#1a-zenodo-mapper-publish-synced-sources)
    - [1b) Zenodo mapper publish (single dataset)](#1b-zenodo-mapper-publish-single-dataset)
    - [2a) CKAN mapper publish (synced sources)](#2a-ckan-mapper-publish-synced-sources)
    - [2b) CKAN mapper publish (single dataset)](#2b-ckan-mapper-publish-single-dataset)
    - [3) Local catalog publisher (`databus_local_manager`)](#3-local-catalog-publisher-databus_local_manager)
  - [Automation](#automation)
  - [Notes](#notes)

## Setup

```bash
uv sync
```

Optional: install [pre-commit](https://pre-commit.com) Git hooks (Ruff + file checks; requires the dev group):

```bash
uv sync --group dev
uv run pre-commit install
```

Ensure you have set all API keys and credentials in the `.env` file (see `.env.dist` for a template).

## Monthly action or manual run

The GitHub action runs once per month and executes mapper publishes.
Alternatively, you can clone the repository and run mapper or local catalog publishes by hand.

- Automation details: [Automation](#automation)
- Mapper commands: [1a) Zenodo mapper publish (synced sources)](#1a-zenodo-mapper-publish-synced-sources), [1b) Zenodo mapper publish (single dataset)](#1b-zenodo-mapper-publish-single-dataset), [2a) CKAN mapper publish (synced sources)](#2a-ckan-mapper-publish-synced-sources), [2b) CKAN mapper publish (single dataset)](#2b-ckan-mapper-publish-single-dataset)

## Publish Commands

### 1a) Zenodo mapper publish (synced sources)

```bash
uv run python -m mappers.zenodo.publish_sources
```

Pre-publish readiness check (queries API and validates payload preparation; no push to Databus):

```bash
uv run python -m mappers.zenodo.publish_sources --dry-run
```

Configuration and adding sources: [`src/mappers/zenodo/README.md`](src/mappers/zenodo/README.md)

### 1b) Zenodo mapper publish (single dataset)

```bash
uv run python -m mappers.zenodo.publish_record \
  --dataset-id "<zenodo-numeric-id>" \
  --group-name "<group-slug>" \
  --group-title "<group-title>" \
  --group-abstract "<group-abstract>" \
  --group-description "<group-description>"
```

### 2a) CKAN mapper publish (synced sources)

```bash
uv run python -m mappers.ckan.publish_sources
```

Pre-publish readiness check (queries API and validates payload preparation; no push to Databus):

```bash
uv run python -m mappers.ckan.publish_sources --dry-run
```

Configuration and adding sources: [`src/mappers/ckan/README.md`](src/mappers/ckan/README.md)

### 2b) CKAN mapper publish (single dataset)

Publish one CKAN dataset by id (explicit CLI). Timestamp bookkeeping uses `--source-id` (top-level registry key) and `--query-id` (defaults match [`src/mappers/ckan/README.md`](src/mappers/ckan/README.md)). In CI, the same command is driven by repository variables — see [`.github/workflows/databus-publish.yml`](.github/workflows/databus-publish.yml).

```bash
uv run python -m mappers.ckan.publish_record \
  --ckan-url "<ckan-base-url>" \
  --dataset-id "<ckan-dataset-id>" \
  --group-name "<group-slug>" \
  --group-title "<group-title>" \
  --group-abstract "<group-abstract>" \
  --group-description "<group-description>" \
  --source-id "world-bank-group" \
  --query-id "wind-topic-datasets"
```

Pre-publish readiness check (queries API and validates payload preparation; no push to Databus):

```bash
uv run python -m mappers.ckan.publish_record \
  --ckan-url "<ckan-base-url>" \
  --dataset-id "<ckan-dataset-id>" \
  --group-name "<group-slug>" \
  --group-title "<group-title>" \
  --group-abstract "<group-abstract>" \
  --group-description "<group-description>" \
  --source-id "world-bank-group" \
  --query-id "wind-topic-datasets" \
  --dry-run
```

### 3) Local catalog publisher (`databus_local_manager`)

Use this when there is no API-backed mapper source and metadata must be curated manually in catalog group files.

Publish to Databus:

```bash
uv run python -m databus_local_manager.publish_local_catalog
```

Recommended pre-check (validate + prepare payloads only, no publish):

```bash
uv run python -m databus_local_manager.prepare_metadata \
  --group-file catalog/groups/ieee-dataport.json
```

## Automation

Monthly workflow: [`.github/workflows/databus-publish.yml`](.github/workflows/databus-publish.yml)

- runs Zenodo mapper publish
- runs CKAN mapper publish

`databus_local_manager` is intentionally manual-run only.

## Notes

- Catalog format is documented in [`catalog/README.md`](catalog/README.md).
- Schemas are under [`src/databus_local_manager/schemas`](src/databus_local_manager/schemas).
- Publishings log is [`catalog/logs/publishings.jsonl`](catalog/logs/publishings.jsonl) and tracked with Git LFS.
