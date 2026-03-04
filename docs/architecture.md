# Architecture Overview

## Design Principles

The architecture is intentionally simple:

- Serverless
- Cheap to run
- Easy to reason about
- Fully reproducible

---

## High Level Pipeline

Data flows through four stages.
Data Source
↓
Raw Data Storage
↓
Transformation Pipeline
↓
Published Dataset
↓
Data & Grit Website


---

## AWS Components

### EventBridge
Triggers scheduled pipeline runs.

Typical schedule:

Monthly refresh.

---

### Lambda Functions

Three logical stages:

#### Ingest
Reads the source dataset and stores it in S3 raw storage.

#### Transform
Performs data cleaning and calculations.

Includes:

- tonne → litre conversion
- currency conversion
- inflation adjustment
- shock phase detection

#### Publish
Writes final datasets for website consumption.

---

### S3 Buckets

Two logical zones:

Raw Zone

raw/london-gasoil/YYYY/MM/DD/source.csv

Curated Zone

global-shocks/v1/london-gasoil/daily.json
global-shocks/v1/heating-oil/estimate.json
global-shocks/v1/events/events.json


### CloudFront

Public datasets are served through CloudFront for:

- caching
- stable URLs
- performance

Example endpoint:


https://data.dataandgrit.energy/global-shocks/v1/london-gasoil/daily.json


---

## Security Model

No secrets are stored in the repository.

AWS authentication uses:

- IAM roles for Lambda
- Parameter Store for configuration
- Secrets Manager for any API keys

---

## Why Serverless?

Advantages:

- low operational overhead
- predictable costs
- ideal for scheduled batch pipelines