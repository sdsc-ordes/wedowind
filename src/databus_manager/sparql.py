import requests

SPARQL_URL_DEFAULT = "https://databus.openenergyplatform.org/sparql"

# SPARQL 1.1 Protocol: query via POST with application/x-www-form-urlencoded (key "query").
# Many triple stores reject JSON bodies {"query": ...} with HTTP 400.


def _sparql_post(sparql_url: str, query: str) -> requests.Response:
    response = requests.post(
        sparql_url,
        data={"query": query},
        headers={"Accept": "application/sparql-results+json"},
        timeout=60,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as err:
        snippet = (response.text or "").strip()
        if len(snippet) > 4000:
            snippet = snippet[:4000] + "..."
        msg = f"{err}\nResponse body from SPARQL endpoint:\n{snippet or '(empty)'}"
        raise requests.HTTPError(msg, response=response) from None
    return response


def sparql_select(sparql_url: str, query: str) -> list[dict[str, str]]:
    response = _sparql_post(sparql_url, query)
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
        <{version_id}> dct:hasVersion ?v .
      }}
    }}
    """
    response = _sparql_post(sparql_url, query)
    return bool(response.json().get("boolean"))
