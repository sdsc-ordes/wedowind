# Data Science Platform

## Intended Usage

For some challenges, a datascience platform is needed. For challenges with big data or with private data from industry. 

Participants from challenges will log in and code in this space. 

## Requirements & Solution

Platforms overviewed but not explored in depth due to lack of fit: 

- [ODAHUB](https://odahub.io) (astrophysics focused, unfriendly to beginner coders)
- [OpenML](https://www.openml.org) (proprietary datasets and workflow, compatibility issues)
- [KNIME](https://www.knime.com) (desktop based)

Platforms explored in detail with requirements: Onyxia and Renku.

| Feature                                                                                  | Onyxia | Renku |
|------------------------------------------------------------------------------------------|--------|--------|
| **Data**                                                                                 |        |        |
| Possibility to manage datasets attached to challenges                                   |   Yes (Kaggle dataset onto s3). also possible to share data across multiple profiles (like a team with access to same s3)   |   Yes (Kaggle dataset onto s3)     |
| Open data search (e.g. EOSC Marketplace integration) and import                         |   No     |     Zenodo integration on its way (ETA next month)   |
| Should accomodate private industry data (soft privacy)                                  |   No: recommended for non-sensitive data only    |     Yes (*P)   |
| **Usage**                                                                               |        |        |
| The platform should be hosted by the provider                                           |   Yes     |   Yes     |
| Possibility to use up to 100 GB in default compute environment and mount external drives|  GPU on demand. first come first serve      |   Free tier: ~4GB (double check). Business model for compute costs: example numbers needed     |
| Google Drive integration                                                                |   No     |   Possibility but not on roadmap     |
| One Drive integration                                                                   |   Yes     |   Not supported     |
| Amazon object storage                                                                   |   Yes     |   Yes     |
| Google Bucket storage                                                                   |   Yes      |   Yes     |
| SQL Databases (Amazon Aurora etc.)                                                      |   Yes     |   Can connect programatically. Credentials managed in platform.     |
| Graph Databases (Neo4j etc)                                                             |   Yes     |   Can connect programatically. Credentials managed in platform.     |
| RDF support                                                                              |   Can connect programatically. Credentials managed in platform.     |  Can connect programatically. Credentials managed in platform.      |
| **Archiving**                                                                            |        |        |
| Integration with public repositories (Zenodo etc.)                                      |  No      |  Not on roadmap but example pull/push from another project is to be made reusable.      |
| Curated repository (like Dryad) with metadata forms (like CEDAR)                        |   NA     |  NA    |
| **Code**                                                                                 |        |        |
| Possibility to set containerised environments for reproducible code executions          |   Yes     |    Yes    |
| Python environments                                                                     |   Yes     |    Yes    |
| Julia environments                                                                      |   Yes     |    Yes    |
| R environments                                                                          |   Yes     |    Yes    |
| Other languages (C++, Rust, Java, etc.)                                                 |   Yes     |    Yes    | 
| Code Notebooks integration (Jupyter etc)                                                |   Yes     |    Yes    | 
| Integration of workflow language(s) for code execution                                  |   Yes     |    Yes   | 
| GitHub or GitLab Integration                                                            |   Yes     |    Yes (both)    |
| **Compute**                                                                              |        |        |
| Possibility to execute lightweight code (e.g. 2CPUs, 8GB RAM), directly on the platform |  Yes      |   Yes (Free Tier is probably sufficient)     |
| Possibility to set up external HPC usage                                               |   No     |    Work ongoing. *HPC    |

*P: Private Data / Code: 

- s3 buckets closed off and user specific. If an admin wants to give access to s3 bucket then the credentials are passed around outside renku platform.
- Same logic for for github repository that is private. Need to connect github account then renku checks if the user has access to a repo

*HPC: 

- several collaborations also require it. By end of year have some features available. 
- Side-note: in ~1month. Being able to connect to personal cloud services: example with Microsoft Azure resources.

## Conclusion

From the current scoping. Renku platform seems to match more requirements than Onyxia platform. The main reasons are:

- Onyxia underlines they do not cater to hosting proprietary data 
- lack of integration to Zenodo
- lack of integration of HPC

The differences remain mild, we recommend to assess costs and to try the UI for preferences.