# Development Rules

These rules should be followed by contributors working on this repository.

## Read first

Before making changes, read:

- `README.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `docs/SCHEMA_NOTES.md` if it exists

## Project boundaries

This repository is a standalone Divinheal data platform.

Do not copy architecture, assumptions, or technical debt from unrelated projects.

The notebook in `notebooks/reference/` is reference material only. Do not convert it directly into production code without review.

## Data quality rules

- Do not invent data.
- Do not silently use fallback data.
- Do not insert fake/stub/default values into final outputs.
- Do not treat AI output as source truth.
- Every important data point should be traceable to a source URL, raw artifact, or manual review record.
- Missing data must be represented explicitly as missing/error/review records.

## Architecture rules

- Do not build one giant all-in-one scraper.
- Keep source adapters separate from dataset pipelines.
- Store raw source artifacts before normalization.
- Keep source-level normalized records separate from dataset-level candidate records.
- Keep candidate records separate from approved records.
- Keep exports separate from source-of-truth records.
- Prefer small source-specific adapters and small dataset-specific pipelines.

## Storage rules

- Use Postgres for structured metadata and records.
- Use object storage for raw artifacts and bulky generated files.
- For local development, mirror object-storage keys under the local `data/` folder.
- Do not hardcode production bucket names or credentials.
- Use environment variables for external service configuration.

## Schema rules

- Treat files in `configs/schemas/` as reference schemas.
- Do not modify uploaded schema CSV files unless explicitly instructed.
- Track schema concerns and proposed changes in `docs/SCHEMA_NOTES.md`.
- Remember that the system must support multiple destination countries, not only India.

## Source rules

Before recommending or implementing a source adapter:

- Confirm what data the source actually exposes.
- Prefer official or high-trust sources where possible.
- Record source limitations.
- Record whether human review is required.
- Do not assume a source has fields that were not verified.

## Code quality rules

- Keep modules small and focused.
- Avoid hardcoded paths where config/env variables are appropriate.
- Use clear statuses for source attempts and records.
- Add tests for core behavior and source adapters when implementation begins.
- Update `docs/DECISIONS.md` when making important architecture decisions.