"""Single source of truth for Databus URLs, limits, and register HTTP helpers."""

from __future__ import annotations

import os
from typing import Any

import requests

DATABUS_URI_BASE = "https://databus.openenergyplatform.org"
DATABUS_REGISTER_URL = f"{DATABUS_URI_BASE}/api/register"
DATABUS_TEXT_LIMITS = {"title": 100, "abstract": 300, "description": 300}
DATABUS_API_KEY_ENV = "DATABUS_API_KEY"
DATABUS_REGISTER_TIMEOUT_S = 120


def databus_api_key(cli_override: str | None = None) -> str | None:
    """Resolve the Databus API key from CLI or environment.

    Parameters
    ----------
    cli_override : str or None
        Value from ``--api-key`` when set.

    Returns
    -------
    str or None
        Non-empty API key, or ``None`` if neither CLI nor
        :data:`DATABUS_API_KEY_ENV` provides one.
    """
    value = (cli_override or "").strip() or os.getenv(DATABUS_API_KEY_ENV)
    return value or None


def post_register_payload(
    payload: dict[str, Any],
    *,
    api_key: str,
    register_url: str | None = None,
    timeout: float = DATABUS_REGISTER_TIMEOUT_S,
) -> None:
    """POST a dataset payload JSON to the Databus register endpoint.

    Parameters
    ----------
    payload : dict[str, Any]
        JSON body (databusclient dataset document).
    api_key : str
        ``X-API-KEY`` header value.
    register_url : str or None, optional
        Override register URL (default: :data:`DATABUS_REGISTER_URL`).
    timeout : float, optional
        Request timeout in seconds (default :data:`DATABUS_REGISTER_TIMEOUT_S`).

    Raises
    ------
    RuntimeError
        When the HTTP response is not OK; message includes response body text.

    Returns
    -------
    None
    """
    url = register_url or DATABUS_REGISTER_URL
    resp = requests.post(
        url,
        json=payload,
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        timeout=timeout,
    )
    if not resp.ok:
        raise RuntimeError(resp.text or f"HTTP {resp.status_code}")
