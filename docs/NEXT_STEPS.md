# Next Steps

This file tracks the immediate next implementation phases after initial project setup.

## Current completed setup

- Standalone repo created: `divinheal-data-platform`
- Git initialized and pushed to GitHub
- Reference schemas copied into `configs/schemas/`
- Reference notebook copied into `notebooks/reference/`
- Planning/reference docs copied into `docs/reference/`
- Core project docs created
- Python project configured with `pyproject.toml`
- Local `.env.example` created
- Virtual environment verified
- Package import verified
- `pytest` and `ruff` verified
- Reference notebooks excluded from Ruff checks

## Immediate next phase

Start building the base implementation layer.

Recommended order:

1. Define initial status constants.
2. Define run context model.
3. Add environment/config loader.
4. Add local artifact storage helper.
5. Add Postgres connection helper.
6. Add first database migration strategy.
7. Add source registry config.
8. Add first source adapter for World Bank population.
9. Add first dataset pipeline for `patient_country_basics`.
10. Export a partial `02_patient_countries.csv`-compatible output.

## First data target

The first data target should be `02_patient_countries.csv`.

Reason:

- It can use non-destination-specific source data.
- World Bank population can support `population_millions`.
- It is low-risk compared to visa rules, doctors, accreditations, testimonials, or cost data.
- It helps test the full source-backed flow without needing messy scraping first.

## Important implementation rules

- Do not silently fill missing fields.
- Do not invent data.
- Store raw source responses before normalization.
- Keep source adapters separate from dataset pipelines.
- Keep source-level records separate from dataset-level records.
- Track statuses and validation errors explicitly.
- Keep exports separate from source-of-truth records.
- Update `docs/DECISIONS.md` when architecture decisions change.

## Suggested first implementation branch

Use a branch such as:

```bash
git checkout -b feature/base-data-platform-core
```

Possible first commit on that branch:

```text
Add core status and run context models
```