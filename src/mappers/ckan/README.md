# CKAN → OEP mapper

Maps CKAN `package_show` / `package_search` results to OEMetadata and publishes to the OEP via OMI.

## Commands

```bash
uv run python -m mappers.ckan.publish_sources --dry-run
uv run python -m mappers.ckan.publish_record \
  --ckan-url "https://energydata.info/en" \
  --dataset-id "<package-name>" \
  --dry-run
```

## Configuration

- Sources: `config/sources.json` (per-source `oep`, `api`, `queries`)
- Checkpoints: `config/timestamp.json`
