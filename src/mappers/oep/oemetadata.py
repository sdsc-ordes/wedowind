"""OEMetadata 2.0 dataclasses (resource, license, contributor, and related parts)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OemetadataDialect:
    """CSV dialect hint for an OEMetadata resource.

    Attributes
    ----------
    delimiter : str, optional
        Field delimiter character. Default is ``","``.
    decimal_separator : str, optional
        Decimal separator character. Default is ``"."``.
    """

    delimiter: str = ","
    decimal_separator: str = "."

    def to_dict(self) -> dict[str, str]:
        """Serialize to an OEMetadata ``dialect`` object.

        Returns
        -------
        dict[str, str]
            Dict with ``delimiter`` and ``decimalSeparator`` keys.
        """
        return {"delimiter": self.delimiter, "decimalSeparator": self.decimal_separator}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> OemetadataDialect:
        """Parse an OEMetadata ``dialect`` dict.

        Parameters
        ----------
        data : dict[str, Any] or None
            OEMetadata ``dialect`` object from a resource dict.

        Returns
        -------
        OemetadataDialect
            Parsed dialect, or defaults when ``data`` is not a dict.
        """
        if not isinstance(data, dict):
            return cls()
        return cls(
            delimiter=str(data.get("delimiter") or ","),
            decimal_separator=str(data.get("decimalSeparator") or "."),
        )


@dataclass
class OemetadataLicense:
    """One OEMetadata ``licenses`` entry.

    Attributes
    ----------
    name : str
        SPDX-style license token (e.g. ``"CC-BY-4.0"``).
    title : str
        Human-readable license title.
    path : str
        License IRI or URL.
    instruction : str, optional
        Usage instruction text. Default is ``"ToDo"``.
    attribution : str, optional
        Attribution requirement text. Default is ``"ToDo"``.
    copyright_statement : None, optional
        Copyright statement. Default is ``None``.
    """

    name: str
    title: str
    path: str
    instruction: str = "ToDo"
    attribution: str = "ToDo"
    copyright_statement: None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an OEMetadata ``licenses`` object.

        Returns
        -------
        dict[str, Any]
            License dict with camelCase keys matching OEMetadata 2.0.
        """
        return {
            "name": self.name,
            "title": self.title,
            "path": self.path,
            "instruction": self.instruction,
            "attribution": self.attribution,
            "copyrightStatement": self.copyright_statement,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OemetadataLicense:
        """Parse an OEMetadata ``licenses`` dict.

        Parameters
        ----------
        data : dict[str, Any]
            Single OEMetadata license object.

        Returns
        -------
        OemetadataLicense
            Parsed license entry.
        """
        return cls(
            name=str(data.get("name") or ""),
            title=str(data.get("title") or ""),
            path=str(data.get("path") or ""),
            instruction=str(data.get("instruction") or "ToDo"),
            attribution=str(data.get("attribution") or "ToDo"),
            copyright_statement=data.get("copyrightStatement"),
        )


@dataclass
class OemetadataContributor:
    """One OEMetadata ``contributors`` entry.

    Attributes
    ----------
    title : str
        Contributor display name.
    path : str or None, optional
        URL or identifier for the contributor. Default is ``None``.
    organization : str or None, optional
        Affiliated organization. Default is ``None``.
    roles : list[str], optional
        OEMetadata role labels. Default is ``["DataCollector"]``.
    date : None, optional
        Contribution date. Default is ``None``.
    oem_object : str, optional
        OEMetadata ``object`` field value. Default is ``"data"``.
    comment : str or None, optional
        Free-text note. Default is ``None``.
    """

    title: str
    path: str | None = None
    organization: str | None = None
    roles: list[str] = field(default_factory=lambda: ["DataCollector"])
    date: None = None
    oem_object: str = "data"
    comment: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an OEMetadata ``contributors`` object.

        Returns
        -------
        dict[str, Any]
            Contributor dict with camelCase keys matching OEMetadata 2.0.
        """
        return {
            "title": self.title,
            "path": self.path,
            "organization": self.organization,
            "roles": self.roles,
            "date": self.date,
            "object": self.oem_object,
            "comment": self.comment,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OemetadataContributor:
        """Parse an OEMetadata ``contributors`` dict.

        Parameters
        ----------
        data : dict[str, Any]
            Single OEMetadata contributor object.

        Returns
        -------
        OemetadataContributor
            Parsed contributor entry.
        """
        roles = data.get("roles")
        return cls(
            title=str(data.get("title") or "").strip(),
            path=data.get("path"),
            organization=data.get("organization"),
            roles=list(roles) if isinstance(roles, list) else ["DataCollector"],
            date=data.get("date"),
            oem_object=str(data.get("object") or "data"),
            comment=data.get("comment"),
        )

    @classmethod
    def from_entries(cls, entries: list[dict[str, Any]]) -> list[OemetadataContributor]:
        """Build contributors from normalized entry dicts.

        Parameters
        ----------
        entries : list[dict[str, Any]]
            Dicts with optional ``title``, ``path``, ``organization``,
            ``roles``, and ``comment`` keys.

        Returns
        -------
        list[OemetadataContributor]
            Contributor objects; entries without a non-empty ``title`` are
            skipped.
        """
        out: list[OemetadataContributor] = []
        for entry in entries:
            title = entry.get("title")
            if not title or not str(title).strip():
                continue
            roles = entry.get("roles")
            out.append(
                cls(
                    title=str(title).strip(),
                    path=entry.get("path"),
                    organization=entry.get("organization"),
                    roles=list(roles) if isinstance(roles, list) else ["DataCollector"],
                    comment=entry.get("comment"),
                )
            )
        return out


@dataclass
class OemetadataContext:
    """WeDoWind / publisher context block on an OEMetadata resource.

    Attributes
    ----------
    title : str, optional
        Context title. Default is ``"WeDoWind"``.
    homepage : str, optional
        Project homepage URL. Default is ``"https://community.wedowind.ch"``.
    documentation : str, optional
        Documentation link or placeholder. Default is ``"ToDo"``.
    source_code : str, optional
        Source repository URL. Default is the wedowind GitHub URL.
    publisher : str, optional
        Publisher name. Default is ``"WeDoWind"``.
    publisher_logo : None, optional
        Publisher logo reference. Default is ``None``.
    contact : str, optional
        Contact information placeholder. Default is ``"ToDo"``.
    funding_agency : None, optional
        Funding agency name. Default is ``None``.
    funding_agency_logo : None, optional
        Funding agency logo reference. Default is ``None``.
    grant_no : None, optional
        Grant number. Default is ``None``.
    """

    title: str = "WeDoWind"
    homepage: str = "https://community.wedowind.ch"
    documentation: str = "ToDo"
    source_code: str = "https://github.com/sdsc-ordes/wedowind"
    publisher: str = "WeDoWind"
    publisher_logo: None = None
    contact: str = "ToDo"
    funding_agency: None = None
    funding_agency_logo: None = None
    grant_no: None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an OEMetadata ``context`` object.

        Returns
        -------
        dict[str, Any]
            Context dict with camelCase keys matching OEMetadata 2.0.
        """
        return {
            "title": self.title,
            "homepage": self.homepage,
            "documentation": self.documentation,
            "sourceCode": self.source_code,
            "publisher": self.publisher,
            "publisherLogo": self.publisher_logo,
            "contact": self.contact,
            "fundingAgency": self.funding_agency,
            "fundingAgencyLogo": self.funding_agency_logo,
            "grantNo": self.grant_no,
        }


@dataclass
class OemetadataSource:
    """Provenance source entry linked from an OEMetadata resource.

    Attributes
    ----------
    title : str
        Source title.
    path : str
        URL or path to the upstream source.
    authors : list[Any], optional
        Author entries. Default is an empty list.
    description : str or None, optional
        Source description. Default is ``None``.
    publication_year : str or None, optional
        Publication year string. Default is ``None``.
    source_licenses : list[OemetadataLicense] or None, optional
        License objects for the upstream source. Default is ``None``.
    """

    title: str
    path: str
    authors: list[Any] = field(default_factory=list)
    description: str | None = None
    publication_year: str | None = None
    source_licenses: list[OemetadataLicense] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an OEMetadata ``sources`` entry.

        Returns
        -------
        dict[str, Any]
            Source dict with camelCase keys matching OEMetadata 2.0.
        """
        return {
            "title": self.title,
            "authors": self.authors,
            "description": self.description,
            "publicationYear": self.publication_year,
            "path": self.path,
            "sourceLicenses": [lic.to_dict() for lic in self.source_licenses]
            if self.source_licenses
            else None,
        }


@dataclass
class OemetadataResource:
    """One OEMetadata resource object (maps to one OEP table).

    Attributes
    ----------
    name : str
        OEP table identifier.
    title : str
        Human-readable resource title.
    path : str
        OEP dataedit URL for the table.
    description : str
        Resource description text.
    topics : list[str]
        OEP topic tags.
    languages : list[str]
        Language codes.
    subject : list[dict[str, Any]]
        Subject classification entries.
    keywords : list[str]
        Keyword tags.
    publication_date : str or None
        ISO ``YYYY-MM-DD`` publication date.
    context : OemetadataContext
        Publisher and project context block.
    licenses : list[OemetadataLicense]
        License objects.
    schema : dict[str, Any]
        OEMetadata table schema.
    dialect : OemetadataDialect
        CSV dialect settings.
    format : str
        File format label (uppercase).
    type : str, optional
        Resource type. Default is ``"table"``.
    encoding : str, optional
        Character encoding. Default is ``"UTF-8"``.
    sources : list[OemetadataSource], optional
        Provenance source entries. Default is an empty list.
    contributors : list[OemetadataContributor] or None, optional
        Contributor objects. Default is ``None``.
    """

    name: str
    title: str
    path: str
    description: str
    topics: list[str]
    languages: list[str]
    subject: list[dict[str, Any]]
    keywords: list[str]
    publication_date: str | None
    context: OemetadataContext
    licenses: list[OemetadataLicense]
    schema: dict[str, Any]
    dialect: OemetadataDialect
    format: str
    type: str = "table"
    encoding: str = "UTF-8"
    sources: list[OemetadataSource] = field(default_factory=list)
    contributors: list[OemetadataContributor] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to an OEMetadata ``resources`` entry.

        Returns
        -------
        dict[str, Any]
            Resource dict with camelCase keys matching OEMetadata 2.0.
            ``sources`` and ``contributors`` are omitted when empty.
        """
        resource: dict[str, Any] = {
            "name": self.name,
            "topics": self.topics,
            "title": self.title,
            "path": self.path,
            "description": self.description,
            "languages": self.languages,
            "subject": self.subject,
            "keywords": self.keywords,
            "publicationDate": self.publication_date,
            "context": self.context.to_dict(),
            "licenses": [lic.to_dict() for lic in self.licenses],
            "type": self.type,
            "format": self.format,
            "encoding": self.encoding,
            "schema": self.schema,
            "dialect": self.dialect.to_dict(),
        }
        if self.sources:
            resource["sources"] = [source.to_dict() for source in self.sources]
        if self.contributors:
            resource["contributors"] = [contributor.to_dict() for contributor in self.contributors]
        return resource

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OemetadataResource:
        """Parse an OEMetadata resource dict.

        Parameters
        ----------
        data : dict[str, Any]
            OEMetadata ``resources`` entry.

        Returns
        -------
        OemetadataResource
            Parsed resource object with nested context, dialect, and
            sources.
        """
        sources = [
            OemetadataSource(
                title=str(s.get("title") or ""),
                path=str(s.get("path") or ""),
                authors=list(s.get("authors") or []),
                description=s.get("description"),
                publication_year=s.get("publicationYear"),
                source_licenses=[
                    OemetadataLicense.from_dict(lic)
                    for lic in (s.get("sourceLicenses") or [])
                    if isinstance(lic, dict)
                ]
                or None,
            )
            for s in (data.get("sources") or [])
            if isinstance(s, dict)
        ]
        context_data = data.get("context") if isinstance(data.get("context"), dict) else {}
        licenses_raw = data.get("licenses") or []
        licenses = [
            OemetadataLicense.from_dict(lic) for lic in licenses_raw if isinstance(lic, dict)
        ]
        contributors_raw = data.get("contributors")
        contributors = (
            [OemetadataContributor.from_dict(c) for c in contributors_raw if isinstance(c, dict)]
            if isinstance(contributors_raw, list)
            else None
        )
        return cls(
            name=str(data.get("name") or ""),
            title=str(data.get("title") or ""),
            path=str(data.get("path") or ""),
            description=str(data.get("description") or "ToDo"),
            topics=list(data.get("topics") or []),
            languages=list(data.get("languages") or []),
            subject=list(data.get("subject") or []),
            keywords=list(data.get("keywords") or []),
            publication_date=data.get("publicationDate"),
            context=OemetadataContext(
                title=str(context_data.get("title") or "WeDoWind"),
                homepage=str(context_data.get("homepage") or ""),
                documentation=str(context_data.get("documentation") or "ToDo"),
                source_code=str(context_data.get("sourceCode") or ""),
                publisher=str(context_data.get("publisher") or "WeDoWind"),
                publisher_logo=context_data.get("publisherLogo"),
                contact=str(context_data.get("contact") or "ToDo"),
                funding_agency=context_data.get("fundingAgency"),
                funding_agency_logo=context_data.get("fundingAgencyLogo"),
                grant_no=context_data.get("grantNo"),
            ),
            licenses=licenses,
            schema=dict(data.get("schema") or {"fields": [], "primaryKey": []}),
            dialect=OemetadataDialect.from_dict(data.get("dialect")),
            format=str(data.get("format") or "CSV"),
            type=str(data.get("type") or "table"),
            encoding=str(data.get("encoding") or "UTF-8"),
            sources=sources,
            contributors=contributors,
        )
