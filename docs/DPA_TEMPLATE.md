# DPA Template (Building Blocks)

## Roles
- Controller: Client
- Processor: TruthShield
- Optional: Joint-Controller assessment for specific collaborations

## Scope & Purpose
- Processing for misinformation detection, triage (HITL), reporting and educational amplification.
- Purpose limitation; no unrelated profiling or automated decision-making without human oversight.

## Data Categories
- Content text, timestamps, platform metadata, pseudonymous IDs (hashed), non-PII metrics.
- Optional evidence snapshots (redacted as needed), audit references.

## Lawful Basis
- Legitimate interest and/or contract performance (as applicable), consent if required by platform policies.

## Technical & Organizational Measures (TOMs)
- Access control (RBAC, least privilege), encryption in transit and at rest.
- Logging & audit trails (append-only, signatures), backup/restore, incident response.
- Data minimization and pseudonymization; transparency labeling for AI-generated content.

## Sub-Processors
- Hosting, build/CI, email, error monitoring (EU/EWR storage where possible); maintained in a separate list.

## Retention & Deletion
- Configurable TTL per data category (raw, derived, labels, reports); secure deletion workflows.
- Hash manifests retained for integrity proofs.

## International Transfers
- EU/EWR-first; Standard Contractual Clauses where applicable; data localization documented.

## Data Subject Rights
- Access, rectification, erasure; contact via legal@truthshield.eu.

