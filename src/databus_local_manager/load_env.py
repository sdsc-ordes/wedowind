"""Load repo `.env` into the process so `DATABUS_API_KEY` is visible to `os.getenv`."""

from __future__ import annotations

from pathlib import Path


def load_dotenv_if_available() -> None:
    """Load ``find_dotenv()`` or repo ``.env`` so ``os.getenv`` sees secrets."""
    try:
        from dotenv import find_dotenv, load_dotenv
    except ImportError:
        return

    path = find_dotenv()
    if path:
        load_dotenv(path)
        return

    repo_dotenv = Path(__file__).resolve().parent.parent.parent / ".env"
    if repo_dotenv.is_file():
        load_dotenv(repo_dotenv)
