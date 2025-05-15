# ML-croissant

[Specification](https://docs.mlcommons.org/croissant/docs/croissant-spec.html)

## Overview
Croissant is a metadata format to make datasets "ML-ready".
In contrast to other dataset vocabularies (e.g. DCAT) and repositories (e.g. CKAN) it focuses on __interoperability__ with other systems via shared dataset representations and __not__ dataset management and organization.


## Structure

ML-Croissant builds on [schema.org/Dataset](https://schema.org/Dataset) with extension for ML usage.
The format has four layer:

- __Metadata__: 
Contains general information about the dataset, such as its name, description and license.
- __Resources__: 
Describes the source data included in the dataset. 
- __Structure__: 
Describes and organizes the structure of the resources.
- __(ML) Semantics__: 
ML-specific data interpretations, including custom data types (e.g., bounding boxes) and dataset organization methods (e.g., train/test splits).


### Metadata layer
This layer contains [schema.org/Dataset](https://schema.org/Dataset) properties and adds features related to Responsible AI (RAI) such as data lifecycle, labeling, safety, fairness, traceability, regulatory compliance, and inclusion.

### Resources layer
Croissant has __two primitive classes__ to describe the resources
contained in a dataset: `FileObject` to describe individual files, and `FileSet` to describe sets of files. They can be used for any "type" of resources, e.g. images, text files, etc.

### Structure layer
To describe the structure of each resource. Adds a `RecordSet` class that defines the source of its data and can link resources, e.g. can link metadat files to raw data.

### Semantics layer:
Provides a general mechanism to attach semantics to data by linking to known vocabularies and identifiers. From a ML perspective, semantic typing is used to describe important aspects, such as splits for test, training and validation, as well as label information.

## Integrations
- [Google Dataset search](https://datasetsearch.research.google.com/) provides a croissant filter.
- [Kaggle dataset](https://www.kaggle.com/datasets) metadata can be downloaded in Croissant JSON-LD. 
- [OpenML dataset](https://www.openml.org/search?type=data) metadata can be downloaded in Croissant JSON-LD.
- [Hugging face dataset](https://huggingface.co/datasets) metadata can be downloaded in Croissant JSON-LD.
- [CKAN](https://ckan.org/) supports Croissant format.
- [Dataverse](https://dataverse.org/) supports Croissant format.


## Tooling
 [Python library](https://github.com/mlcommons/croissant/tree/main/python/mlcroissant):
- Programmatically write your JSON-LD Croissant files.
- Verify your JSON-LD Croissant files.
-  Load data from Croissant datasets.

[Croissant editor](https://huggingface.co/spaces/MLCommons/croissant-editor):
- Inspect, create or modify croissant descriptions.
- auto-derive metadata for fine-tuning.

[`CroissantBuilder()`](https://www.tensorflow.org/datasets/format_specific_dataset_builders#croissantbuilder): 
- generate [TensorFlow datasets](https://www.tensorflow.org/datasets/overview) from Croissant format.
