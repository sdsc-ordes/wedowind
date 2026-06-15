"""Load repo ``.env`` so ``OEP_API_TOKEN`` and other secrets are visible to ``os.getenv``."""

from __future__ import annotations

from pathlib import Path


def load_dotenv_if_available() -> None:
    """Load environment variables from a ``.env`` file when python-dotenv is installed.

    Uses :func:`dotenv.find_dotenv` when a file is found on the search path;
    otherwise loads the repository root ``.env`` relative to this package.

    Returns
    -------
    None
    """
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
