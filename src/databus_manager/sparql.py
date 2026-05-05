import requests

SPARQL_URL_DEFAULT = "https://databus.openenergyplatform.org/sparql"

def sparql_select(sparql_url: str, query: str) -> list[dict[str, str]]:
    response = requests.post(
        sparql_url,
        json={"query": query},
        headers={"Content-Type": "application/json", "Accept": "application/sparql-results+json"},
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    rows: list[dict[str, str]] = []
    for b in payload.get("results", {}).get("bindings", []):
        rows.append({k: v.get("value", "") for k, v in b.items()})
    return rows


def sparql_remote_version_exists(version_id: str, sparql_url: str) -> bool:
    query = f"""
    PREFIX dct: <http://purl.org/dc/terms/>
    ASK {{
      GRAPH ?g {{
        BIND(<{version_id}> AS ?dataset)
        ?dataset dct:hasVersion ?v .
      }}
    }}
    """
    response = requests.post(
        sparql_url,
        json={"query": query},
        headers={"Content-Type": "application/json", "Accept": "application/sparql-results+json"},
        timeout=60,
    )
    response.raise_for_status()
    return bool(response.json().get("boolean"))

