# Zenodo → OEP mapper

Maps Zenodo `/api/records` to [OEMetadata 2.0](https://github.com/OpenEnergyPlatform/oemetadata) and publishes to the Open Energy Platform via [OMI](https://github.com/OpenEnergyPlatform/omi).

## Commands

```bash
uv run python -m mappers.zenodo.publish_sources --dry-run
uv run python -m mappers.zenodo.publish_record --dataset-id "<zenodo-id>" --dry-run
```

## Configuration

- Sources: `config/sources.json` (`defaults.oep`, `sources` query params)
- Checkpoints: `config/timestamp.json`

## API

- `GET /api/records` — list records per source
- `GET /api/records/{id}` — single record for mapping

See [`README_incompatibilities.md`](../../../README_incompatibilities.md) at the repo root.
