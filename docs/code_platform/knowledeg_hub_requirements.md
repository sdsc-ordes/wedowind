# Knowledge Hub Requirements – Platform Comparison

Legend (cell colours in the original):

- 🟢 fulfilled
- 🟠 partially fulfilled / unclear
- 🔴 not fulfilled
- ⚪ not applicable / not assessed

Platforms compared: Open Energy Platform (OEP), WindLab (Knowledge & Data Hub), WETO Software Stack, Wind Data Hub, Renku, DataHub.

## User story: Analyst in Industry

### Data Requirements

| Requirement | Open Energy Platform | WindLab | WETO Software Stack | Wind Data Hub | Renku | DataHub |
|---|---|---|---|---|---|---|
| Find dataset using advanced search | 🟢 | 🟢 | ⚪ NA. software only | 🟢 | 🟢 | 🟢 |
| Benchmarking to dataset * | 🔴 | 🔴 | ⚪ NA. software only | 🔴 | 🟠 can set-up a benchmark platform? | 🟠 |
| Ontology to define metadata | 🟢 | 🟢 | ⚪ NA. software only | 🔴 | 🔴 | 🟠 |
| Metadata Form for easy fill out. Present at the same place as data upload. | 🟢 | 🟠 scraping mechanism for co-organizations | ⚪ NA. software only | 🔴 | ⚪ NA. Not designed for upload. | 🟠 No data storage (metadata-only) |
| SPARQL engine to query metadata | 🟢 | 🔴 | ⚪ NA. software only | 🔴 | ⚪ NA. no RDF | 🔴 |

### Code Requirements

| Requirement | Open Energy Platform | WindLab | WETO Software Stack | Wind Data Hub | Renku | DataHub |
|---|---|---|---|---|---|---|
| Find code using advanced search | 🟢 | ⚪ Na, no software | 🟢 | 🟢 | 🟢 | 🟢 |
| Ontology to define code which is tied to data metadata types (know which code can use what data) | 🟢 | ⚪ Na. no software | 🟢 | 🔴 | 🔴 | 🟠 |
| Code Metadata form for easy fill out. With GitHub API ping | 🟢 | ⚪ Na. no software | 🔴 | 🔴 | ⚪ NA. Not designed for upload. | 🟢 |
| SPARQL engine to query metadata | 🟢 | ⚪ Na. no software | 🔴 | ⚪ NA. no RDF | ⚪ NA. no RDF | 🔴 |

### Community Requirements

| Requirement | Open Energy Platform | WindLab | WETO Software Stack | Wind Data Hub | Renku | DataHub |
|---|---|---|---|---|---|---|
| R&D between industry and researchers | 🔴 About section mentions primarily academic partners. Bringing in industry could be WeDoWind’s added value to joining the network | 🟠 Looks like they have lots of governmental partners but industry? | 🟢 | 🟢 | 🟢 | ⚪ |
| Interoperable with json-schema/open-api endpoints (for potential transformation of jsonschema to RDF) | 🟢 can be submitted to code catalog. For associated datasets, can match the json schema terms to the existing OEP ontology | 🔴 | 🔴 | 🔴 | 🟢 | 🟢 |
| WeDoWind Role: Approach a dataset / code with a challenge opportunity. Challenge prep: post metadata of code and data on the knowledge Hub so it can be findable for and post the challenge. | 🟢 | 🟠 possible to post dataset | 🔴 currently not designed to post externals | 🔴 currently not designed to post externals | 🟢 Appropriate for challenges | 🟢 |
| Open source based | 🟢 | 🟠 | 🔴 | 🔴 | 🟢 | 🟢 |

## User story: TWEED PhD Student

### Data Requirements

| Requirement | Open Energy Platform | WindLab | WETO Software Stack | Wind Data Hub | Renku | DataHub |
|---|---|---|---|---|---|---|
| Data parsing (PDF of the manual of a wind turbine) to graphs (currently RDF). * | 🔴 | 🔴 | 🔴 | 🔴 | 🟠 Possible to create the code to do that in Renku | 🔴 |
| Private data from Industry: only publish Metadata for private data and contact point to request data * | 🟠 not sure. you can probably upload a blank CSV and put only the metadata | 🟠 gather metadata only but need access to the private industry system ? | 🔴 currently not designed to post externals | 🔴 currently not designed to post externals | 🟢 Allow private projects | 🟢 |
| Open-source based | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ | ⚪ |
