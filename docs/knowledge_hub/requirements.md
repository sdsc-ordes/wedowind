# Knowledge Hub

## Aim
A catalogue-like resource to collect and find relevant datasets and software/code repositories.

## Existing approaches
- [WETO stack](https://nrel.github.io/WETOStack/index.html)
  + NREL
  + curated list of internal models/code repositories
  + includes FAIR score and simple schema
- [Open Energy data initiative (OEDI)](https://data.openei.org/)
- [WindLab](https://windlab.hlrs.de/)
  + europe
  + datasets, organizations, no code
- [Wind Data Hub](https://wdh.energy.gov/home)
  + NREL
  + code (github stats) + datasets (broken links?)

## Requirements

### Use cases
- __AI__: Support model development, training and improvement
- __Stats__: Support physics/hybrid model development and improvement
- __Real data__: Learning about working with real data
- __Internal__: Running internal benchmarks
- __Logistiks__: Optimising logistics and installation (?)
- __Retrofit__: Planning retrofit campaigns (?)
- __Monitoring__: Portfolio monitoring
- __CS__: Citizen science
- __Community__: Building community trust
- __Lifecycle__: Lifecycle tracking


### Features

| Feature | Ideas | Exists |
| -------- | -------- | -------- |
| __AI/Teaching__: standardized, ML-readable metadata | Plaza, ontology, ML-croissant?    |   :white_check_mark: WETO stack   |
| __AI__: dev environment integration  | renku, huggingface? connection   |   :red_circle:    |
 __AI__: provide comp. resources  | renku connection*   |   :red_circle:    |
| __AI/Stats__: versioning |     |   :red_circle:    |
| __AI/Stats__: performance metrics |  **   |  :question: WETO stack    |
| __AI/Stats/Monitoring__: usage metrics |  gimmie, dataset? (zenodo, renku stats?)   |  :white_check_mark: Wind Data Hub (github metrics)    |
 | __Real data__: data + compute env |  renku connection   |  :red_circle:    |
 | __Teaching__: example data usage |  renku connection  |  :question:    |
 | __Internal__: data access control |  renku connection  |  :white_check_mark: Wind Data Hub    |
 | __CS/Community__: communities | OpenPulse?    |  :white_check_mark: Wind Lab    |
 | __CS/Community__: allow contributions | GH issues, plaza submission form*/***    |  :red_circle:     |
 | __Lifecycle__: continuous testing | \*    |  :red_circle:     |
 | dataset hosting | zenodo    |  :question:     |
 | data preview | renku connection (?)   |  :red_circle:     |
 | data + code integration | renku connection (?)   |  :red_circle: |
 | data/code + paper integration | renku connection (?) | :red_circle: |
 | publish and access code | git! | :red_circle: |
 | testing/validating code/software | * | :red_circle: |
 | compare code/software | ** | :red_circle: |
 | develope code/software | --> datascience platform | :red_circle: |


  \* requires resources (e.g. money, deployment/maintanence, ..)
  \** can we link to the challenges/challenge results here?
  \*** requires user authentication

 ### Metadata

 (apply to both data and code)

| Type | Detail | Source |
| -------- | -------- | -------- |
| application     | programming language, downloads,..    | gimmie, wind data hub    |
| life cycle     | realeses, ..   | gimmie, wind data hub    |
| quality, usability    | ?   | WETO stack form    |
| contact    | maintainer/owner   | gimmie, FAIR score (plaza)    |
| FAIRness    | ?   | FAIR score (plaza)    |
| License    | license, license explanation   | gimmie    |
| Data formats    | input/output data  | ?   |


### Comments

*Many academic papers has python code attached. Can you enable an system so this codes an be imbedded and teste towards data. A lot of value is in this papers.*

*There are several different "data platforms" in play already - e.g. for resource data, ocean data, SCADA data, financial data... some open and some proprietary. So I think defining the use case first is a must. There's also a risk here of scope creep, I was inclined to tick all boxes, as its like a wish list!*
