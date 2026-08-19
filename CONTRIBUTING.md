# Contributing to the Chubb Ontology Governance Demo

This repository is an illustrative engineering reference for governed enterprise ontology development. Do not place confidential Chubb data, credentials, production endpoints, or regulated data in this repository.

## Developer workflow

1. Create a branch from `main`: `git checkout -b feature/ONTO-452-cyber-policy`.
2. Update the authoritative artifact under `ontology/`, `vocabulary/`, or `shapes/`.
3. Run `python scripts/govern.py` locally.
4. Review `reports/latest/change-report.md`.
5. Add or update the business change record using `changes/CHANGE_TEMPLATE.yaml` when required by your enterprise process.
6. Commit with the ticket ID, for example `ONTO-452 Add CyberPolicy`.
7. Push the branch and open a pull request.
8. CI runs the same governance gate. Semantic changes require the approval level configured in `governance/ontology-governance.yaml`.
9. After approval and merge, use the controlled release process. Never edit `releases/` manually.

## Semantic version policy

- PATCH: annotations/documentation that do not change logical meaning.
- MINOR: backward-compatible additions such as a new class, property, or controlled term.
- MAJOR: removals or inference-sensitive changes to existing terms, including superclass, domain/range, disjointness, cardinality, or stable IRI changes.

## Stable IRI rule

Do not create `Policy_v2`, `Claim_2026`, or environment-specific term IRIs. Keep the canonical enterprise term IRI stable and version the ontology/module release.
