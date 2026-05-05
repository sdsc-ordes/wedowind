# catalog

Active catalog used by Databus-first sync.

## Structure

```text
catalog/
├── .databus/
│   ├── discrepancies.jsonl
│   └── publish_ledger.jsonl
├── group-<slug>/
│   ├── group-metadata.jsonld
│   ├── artefacts-<n>/
│   │   ├── artefact-metadata.jsonld
│   │   ├── version-<m>/
│   │   │   └── version.jsonld
│   │   └── ...
│   └── ...
└── README.md
```

Notes:

- **`group-metadata.jsonld`** — Group node (`title`, `abstract`, `description`).
- **`artefacts-<n>/artefact-metadata.jsonld`** — Artifact node with the same three
  fields; `@id` must be the artefact URI (version `@id` without the final version
  segment).
- Version **`@id`** remains `.../<group>/<artifact>/<version>`.
- Discrepancy logs use field names from those JSON-LD properties (`entity_type`:
  `group`, `artefact`, or `version`).

## Sync order

1. Compare catalog metadata with OEP Databus (SPARQL).
2. Append field-level discrepancy rows to `.databus/discrepancies.jsonl` when a
   remote copy exists and any metadata field differs (schema:
   `src/schemas/discrepancy.schema.json`).
3. Pull remote values into local files when applying changes (not `--dry-run`)
   and mismatches exist (Databus wins).
4. Classify catalog entries with local ledger + remote checks.
5. Publish only `new` versions.
6. Append successful publishes to `.databus/publish_ledger.jsonl` (schema:
   `src/schemas/publishing.schema.json`).

## Commands

Dry run:

```bash
uv run python -m databus_manager.sync_catalog_with_databus --dry-run
```

Pull only:

```bash
uv run python -m databus_manager.sync_catalog_with_databus --pull-only
```

Full sync + publish:

```bash
uv run python -m databus_manager.sync_catalog_with_databus
```
