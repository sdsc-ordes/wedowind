DATABUS_URI_BASE = "https://databus.openenergyplatform.org"


class GroupMetadata:
    def __init__(self, name: str, title: str, abstract: str, description: str):
        self.name = name
        self.title = title
        self.abstract = abstract
        self.description = description


def get_databus_identifier(
    account_name: str, group: str, artifact_name: str, version: str | None = None
):
    identifier = f"{DATABUS_URI_BASE}/{account_name}/{group}/{artifact_name}"
    if version:
        identifier += f"/{version}"
    return identifier
