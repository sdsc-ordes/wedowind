# databus_local_manager

`databus_local_manager` is the local-catalog publish pipeline.

## Contents

- [databus\_local\_manager](#databus_local_manager)
  - [Contents](#contents)
  - [What it does](#what-it-does)
  - [Main commands](#main-commands)

## What it does

- Scans `catalog/groups/*.json`
- Validates group files against `databus_local_manager/schemas/catalog.schema.json`
- Prepares databusclient payloads from human-readable JSON fields
- Classifies versions via `catalog/logs/publishings.jsonl` (`published` vs `new`)
- Publishes only `new` versions to the Databus register endpoint
- Appends successful publishes to `publishings.jsonl`

## Main commands

Dry run:

```bash
uv run python -m databus_local_manager.publish_local_catalog --dry-run
```

Publish:

```bash
uv run python -m databus_local_manager.publish_local_catalog
```

Prepare one group file (validate + build payloads only):

```bash
uv run python -m databus_local_manager.prepare_metadata --group-file catalog/groups/ieee-dataport.json
```
