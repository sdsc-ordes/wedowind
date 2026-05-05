"""OEP Databus endpoints and defaults (adjust if your instance differs)."""

from __future__ import annotations

# Open Energy Platform Databus
BASE_URL = "https://databus.openenergyplatform.org"
REGISTER_URL = f"{BASE_URL}/api/register"
CONTEXT_URL = f"{BASE_URL}/res/context.jsonld"
SPARQL_URL = f"{BASE_URL}/sparql"

DEFAULT_CATALOG = "catalog"
LOG_DIR_RELATIVE = ".databus/logs"
