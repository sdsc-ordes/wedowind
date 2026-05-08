import databusclient
from ckanapi import RemoteCKAN

from mapper.utils import GroupMetadata, get_databus_identifier


# CKAN
class CKANToDataBusMapper:
    def __init__(self, ckan_url, apikey: str | None = None):
        self.ckan = RemoteCKAN(ckan_url)

    def map_to_dataset(self, dataset_id: str, group: GroupMetadata) -> str:

        dataset = self.ckan.action.package_show(id=dataset_id)

        distributions = []
        for res in dataset.get("resources", []):
            distributions.append(
                databusclient.create_distribution(
                    url=res["url"],
                    cvs={"type": res["resource_type"]},
                    file_format=res["format"],
                )
            )

        artifact_name = dataset["name"]
        version = dataset.get("version") or dataset.get("metadata_modified")
        version_id = get_databus_identifier(group.name, artifact_name, version)
        dataset = databusclient.create_dataset(
            version_id,
            title=dataset["title"],
            abstract=dataset["topic"],
            description=dataset["notes"],
            license_url=dataset.get("license_id") or dataset.get("license_url"),
            distributions=distributions,
            group_title=group.title,
            group_abstract=group.abstract,
            group_description=group.description,
        )
        return dataset
