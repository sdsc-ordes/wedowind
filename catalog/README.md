# catalog

Local JSON catalog consumed by
[`databus_local_manager.publish_local_catalog`](../src/databus_local_manager/publish_local_catalog.py).

## Structure

```text
catalog/
├── groups/
│   ├── <group>.json
│   └── ...
├── logs/
│   └── publishings.jsonl
└── README.md
```

`groups/*.json` files are validated against
[`catalog.schema.json`](../src/databus_local_manager/schemas/catalog.schema.json).

## Group File Contract

Each group file is plain JSON and must contain:

- `group`: metadata object with `id`, `title`, `abstract`, `description`
- `artifacts[]`: list of artifacts
- `artifacts[].versions[]`: list of publishable versions
- `artifacts[].versions[].distributions[]`: download entries

All identifiers (`group.id`, `artifact.id`, `version.id`) are full Databus URIs.

## Publishing Log Contract

`catalog/logs/publishings.jsonl` is append-only and contains one JSON object per
successfully published version, using this shape:

```json
{
  "timestamp": "2026-01-01T00:00:00+00:00",
  "entity_id": "https://databus.openenergyplatform.org/.../v1.0.0",
  "entity_type": "version"
}
```

Versions are considered already published when their `entity_id` exists in this file.

## Pipeline Behavior

`publish_local_catalog` performs:

1. scan `catalog/groups/*.json`
2. schema validation
3. payload preparation via `databusclient`
4. classification against `publishings.jsonl`
5. publish only new versions
6. append one publishing row per successful publish

On register API errors, the script prints `[publish] failed:` and the response body.

## Commands

Dry run (scan, validate, prepare, classify; no network publish):

```bash
uv run python -m databus_local_manager.publish_local_catalog --dry-run
```

Publish new versions:

```bash
uv run python -m databus_local_manager.publish_local_catalog
```

Validate and prepare a single group file:

```bash
uv run python -m databus_local_manager.prepare_metadata \
  --group-file catalog/groups/zenodo.json
```
