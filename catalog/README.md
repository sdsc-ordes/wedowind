# catalog

Folder layout and JSON-LD shapes used by
[`sync_catalog_with_databus`](../src/databus_manager/sync_catalog_with_databus.py)
(scan → compare vs OEP Databus → classify → publish). See the [root README](../README.md)
for the full module map (`scan_catalog`, `compare_catalog_with_databus`,
`publish_group_metadata`, etc.).

## Structure

```text
catalog/
├── logs/
│   ├── discrepancies.jsonl
│   └── publishings.jsonl
├── group-<slug>/
│   ├── group-metadata.jsonld
│   ├── artifact-<slug>/
│   │   ├── artefact-metadata.jsonld
│   │   ├── version-<m>/     # or v<semver>/ (e.g. v1.2.0/)
│   │   │   └── version.jsonld
│   │   └── ...
│   └── ...
└── README.md
```

Notes:

- **`group-metadata.jsonld`** — Group node (`title`, `abstract`, `description`).
- Under each group, artefact directories are **`artifact-<slug>/`** (see tree above).
- **Artifact metadata file** — **`artefact-metadata.jsonld`** or **`artifact-metadata.jsonld`**: Artifact node (`title`, `abstract`, `description`); `@id` must be the artefact URI (version `@id` without the final version segment).
- Version **`@id`** remains `.../<group>/<artifact>/<version>`.
- Discrepancy logs use field names from those JSON-LD properties (`entity_type`:
  `group`, `artefact`, or `version`).

## Sync order

1. Compare catalog metadata with OEP Databus (SPARQL).
2. Append field-level discrepancy rows to `logs/discrepancies.jsonl` when a
   remote copy exists and any metadata field differs (schema:
   `src/schemas/discrepancy.schema.json`).
3. Pull remote values into local files when applying changes (not `--dry-run`)
   and mismatches exist (Databus wins).
4. Classify catalog entries with local publishings + remote checks.
5. Publish only `new` versions.
6. Append successful publishes to `logs/publishings.jsonl` (schema:
   `src/schemas/publishing.schema.json`).

### Compare vs `publishings_mismatch`

Compare/pull reconciles **catalog files** with Databus. **`publishings.jsonl`** is a
separate append-only record of **successful registers from this automation** (by
default one row per published **version** `@id`). They do not track the same thing:
pulling metadata **does not** add publishings rows. So **`publishings_mismatch`**
(remote version exists on SPARQL, version `@id` missing from publishings) can still
appear—for example after a version was registered elsewhere, or this repo was cloned
without `catalog/logs/publishings.jsonl`.

| Situation | What happens |
|-----------|----------------|
| **Typical `publishings_mismatch`** | The version exists on Databus and you already have `group-*` / `artifact-*` / `version.jsonld` locally, but `publishings.jsonl` has no row. Compare can pull into those **existing** files when apply is on and there’s a mismatch. |
| **Only on Databus, nothing in `catalog/`** | That version never appears in scan/classify (no local `version.jsonld`). No `publishings_mismatch` row for it from this pipeline. Nothing here **creates** the catalog layout from remote. |

### Publishings and new groups

There is **no separate “publish group only” step.** Introducing a new group on
Databus happens together with the **first version** you publish: `publish_group_metadata`
reads `group-metadata.jsonld` and the chosen `version.jsonld`, builds one register
payload (`create_dataset`), and POSTs group, artifact, and version metadata in a
**single** request.

After a successful publish, **`sync_catalog_with_databus` appends one publishings row
keyed by the version URI** (`entity_type: version`). That line records that this
sync run published that version—even though the HTTP body also carried group
fields. Classify treats **`in_publishings`** as “this **version** `@id` appears in
publishings,” not group or artifact URIs.

The publishings schema allows `group` / `artefact` / `version` rows; the sync
pipeline today **only writes version rows**. Separate group-only publishings rows would
be manual or a future convention and are **not** used by classify for version status.

### Publish failures (SHACL)

Validation happens at the register API. On non-success, **`publish`** / **`sync_catalog_with_databus`**
print **`[publish] failed:`** plus the response body (often SHACL validation detail).

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

Override paths with `--publishings` and `--discrepancy-log` if needed.

Publish a **single** version file (bypasses sync orchestration; uses
`publish_group_metadata`; does not append `publishings.jsonl` unless you run **sync**):

```bash
uv run python -m databus_manager.publish_group_metadata \
  --version-file catalog/group-zenodo/artifact-15471425/version-1.2.0/version.jsonld
```
