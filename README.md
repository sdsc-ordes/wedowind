# wedowind

Research Data Infrastructure for the WeDoWind community.

## Dependency management

Python dependencies are managed with **[uv](https://docs.astral.sh/uv/)** ([`pyproject.toml`](pyproject.toml) + [`uv.lock`](uv.lock)). Install uv (see the [install guide](https://docs.astral.sh/uv/getting-started/installation/)), then from the repository root:

```bash
uv sync
```

Run tools with `uv run …` so they use the project environment (or activate `.venv` after `uv sync`).

When you add or upgrade dependencies, edit [`pyproject.toml`](pyproject.toml), run **`uv lock`**, and commit the updated [`uv.lock`](uv.lock) with your change.

## Publishing metadata to Databus

This repository includes a **catalog** of JSON-LD templates and Python tooling (`databus_manager` under [`src/databus_manager/`](src/databus_manager/)) to sync metadata to the **Open Energy Platform Databus** (`databus.openenergyplatform.org`). CI runs a dry-run sync on relevant changes and uploads log artifacts.

**Full setup, folder layout, GitHub secrets, module map, logs, and troubleshooting:** see **[catalog/README.md](catalog/README.md)**.

Quick start:

```bash
uv sync
uv run python -m databus_manager --catalog catalog
```
