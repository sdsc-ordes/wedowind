# Code Platform

## Intended Usage

Purpose:

- publishing code in a standardized manner
- accessing code
- sharing code as a community

## Requirements

"An open platform that can be accessed from the communication platform, allows data to be published and assigned with metadata based on the developed ontologies." (from proposal components)

- open
- contributions
- versioning
- templating
- ci
- licenses

## Solutions

### Github organization

[Github community tools and guidelines](https://docs.github.com/en/communities)
Github organization allow:

- team collaboration
- branding/common namespace
- projects, issue tracking etc.
- assignment of moderators

### Repository templates 

Repository templates help to standardize contributions to ensure any wedowind project/contribution contains a license, code of conduct, etc. or can be used to distribute common code elements that help to get started. They can be used on the organizational or subspace (e.g. challenge) level.

#### Github Organization Documentation Repository

In the form of a markdown repository, with the main branch protected. Only moderators of the organization can edit these.

- [ ] Code of conduct
- [ ] [Guidelines for structuring an open-source repository](https://swissdatasciencecenter.github.io/best-practice-documentation/docs/chapters/dev-practice/repository-guideline/oss-repo)
- [ ] Guidelines for versioning code (through releases and tags)
- [ ] Kaggle guidelines that explain the usage of the repository template (detailed below). These Kaggle guidelines would then be used in every challenge

#### Suggested components for the repository template (inside 1 repository)

- [ ] The core would be a fork from the [best practice repository template](https://github.com/sdsc-ordes/repository-template) developed by SDSC ORDES team (intended usage mainly for the python version, but accomodating for other coding languages as well.)

**Documentation related**:

- [ ] template README, notably referencing the general code of conduct and contribution guidelines
- [ ] Choose default license (link coming soon)
- [ ] Under docs: contribution guidelines for good practices on how to contribute to a code repository as an external

**CI related (CI = Github Action)**:

- [ ] CI for deploying mkdocs for a project
- [ ] CI for building a docker image for the project (with main librairies pre-installed)

**Code review and issues related**:

- [ ] Add issue/PR templates  # is this needed

**Hugging Face Related**:

- [ ] README formatting for Hugging Face
- [ ] CI for publishing to a WeDoWind Hugging Face Space
- [ ] Code snippets for accessing a Hugging Face model for inference, for accessing a Hugging Face Dataset

**Data Integration Related**:

- [ ] CI / Code snippets for uploading / downloading from Zenodo / other DB
- [ ] CI / Code snippet for integrating to RDF DB

**Template USAGE**: once the template is defined, for each Kaggle competition, any Kaggle challenge participant would be able to fork from it to start there challenge code.

**Side-note** : Not all components may be compatible with the Renku platform, as it relies on running on docker. A Renku specific repository template (probably a simplified version of the one detailed above) may need to be created for the challenges running on the data science platform.

### Sponsorship

Github offers sponsorships for users to support their open source solutions: [Github sponsors](https://github.com/sponsors)


### Links

- [Open source community guidleines](https://opensource.guide/building-community/)

#### Todo

- [ ] Setup wedowind github organization
- [ ] Define repository template
- [ ] Assign moderators
- [ ] Write Kaggle challenge guidelines which use the repository guidelines
