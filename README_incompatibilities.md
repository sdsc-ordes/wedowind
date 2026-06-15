# OEMetadata mapping incompatibilities (Zenodo / CKAN → OEP)

This document lists gaps between [OEMetadata 2.0](https://github.com/OpenEnergyPlatform/oemetadata/blob/production/oemetadata/latest/metadata_key_description.md) / [OEP](https://openenergyplatform.org) requirements and what Zenodo or CKAN APIs expose. The mappers in `src/mappers/*/oep_mapper.py` fill missing fields with defaults, `null`, or `ToDo` as allowed by the specification.

Publishing uses [OMI](https://github.com/OpenEnergyPlatform/omi) (`update_oep_tables_from_dataset_metadata` → `POST /api/v0/tables/{table}/meta/`).

## Automated provisioning (implemented)

| Step | What happens | Data source |
|------|----------------|-------------|
| Schema inference | Stream **first 2 lines** (configurable) from each **Zenodo/CKAN file URL**; infer `schema.fields` via OMI / Frictionless; sample is held in memory only and not saved | Real remote dataset file |
| Empty OEP table | `PUT /api/v0/tables/{name}/` with column definitions; **no rows uploaded** to OEP | Inferred schema (+ OEP `id` `bigserial` if missing) |
| Metadata push | `POST /api/v0/tables/{name}/meta/` with full OEMetadata | Mapper + inferred schema |

This replaces the manual “create tables in the wizard first” step. It is **not** the same as copying Zenodo/CKAN data onto the OEP: only table structure is registered, matching an empty CSV upload in the wizard.

CLI flags: `--no-infer-schema`, `--no-provision-tables`, `--schema-sample-lines N`.

## Prerequisites / remaining gaps

| Topic | OEMetadata / OEP expectation | Zenodo / CKAN | Mapper behaviour |
|-------|------------------------------|---------------|------------------|
| Non-tabular files | Column schema from data | `.zip`, `.nc`, etc. | Schema inference skipped; empty OEP table with auto `id` only |
| Ontology (`subject`, field `isAbout`) | Platinum-tier IRIs | Not in APIs | Default energy subject; per-field ontology `ToDo` / null |
| Peer review (`review`) | OEP review URL and badge | Not available | Omitted |
| Resource `@id` (Databus-style) | Artifact URI on databus | Not on Zenodo/CKAN | Omitted |
| Full data on OEP | Optional data upload | Files stay at source URL | `sources[].path` points to Zenodo/CKAN download URL |
| License text | `instruction`, `attribution` | Partial | Often `ToDo` |
| Delimiter mismatch | OMI inspect defaults to `;` in some paths | CSV may use `,` | Mapper sniffs delimiter from header before infer |

## Partially mappable fields

| Key | Cardinality / badge | Zenodo | CKAN | Notes |
|-----|---------------------|--------|------|-------|
| `name` (dataset) | [1] Iron | Derived from record id + prefix | Derived from package name + prefix | Title uses human-readable name |
| `name` (resource / table) | [1] Iron | From filename slug | From resource name slug | Must match provisioned OEP table |
| `title`, `description` | Bronze | `metadata.title`, `metadata.description` | `title`, `notes` | HTML stripped |
| `publicationDate` | Bronze | `publication_date` or `created` | `metadata_created` | ISO date when parseable |
| `licenses` | Gold | `metadata.license` | `license_url` / `license_id` | Mapped to OEMetadata license objects |
| `keywords` | Silver | `metadata.keywords` + tags | package tags + provenance | |
| `contributors` | — | `creators` | `author` | Best-effort |
| `schema.fields` | Iron/Silver | Not in API | Not in API | Inferred from **2-line sample** of source file when tabular |

## Zenodo-specific

- **Checksums**: Source file checksums are not copied into OEMetadata.
- **Large files**: Schema sample uses streaming; very wide rows may hit `schema_sample` byte cap (256 KiB).
- **Version lineage**: Not mapped to `schema.foreignKeys`.

## CKAN-specific

- **Resource format**: Values like `SHP ZIP` are not tabular; placeholder table only.
- **Multiple resources**: One OEP table per CKAN resource with a URL.

## Validation

Before push, mappers call `omi.validation.validate_metadata` unless `--skip-validation` is passed. Inferred schemas may trigger optional-field warnings (e.g. missing `@id`).

## References

- OEMetadata example: [example.json](https://github.com/OpenEnergyPlatform/oemetadata/blob/production/oemetadata/latest/example.json)
- OEP API table create: [API Tutorial 02](https://openenergyplatform.github.io/academy/tutorials/01_api/02_api_upload/)
- OMI: `omi inspect` / `infer_metadata` / `push-oep-all`
