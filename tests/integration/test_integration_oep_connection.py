from __future__ import annotations

import os

import requests

def test_can_connect_to_oep_register_with_env_key() -> None:
    api_key = os.getenv("DATABUS_API_KEY")
    assert api_key, "DATABUS_API_KEY must be set for OEP register connectivity test."

    resp = requests.post(
        "https://databus.openenergyplatform.org/api/register",
        json={},
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        timeout=30,
    )
    assert resp.status_code < 500


def test_can_ping_sparql_endpoint() -> None:
    resp = requests.post(
        "https://databus.openenergyplatform.org/sparql",
        json={"query": "ASK {}"},
        headers={"Content-Type": "application/json", "Accept": "application/sparql-results+json"},
        timeout=30,
    )
    assert resp.status_code < 500
    payload = resp.json()
    assert "boolean" in payload or "results" in payload
