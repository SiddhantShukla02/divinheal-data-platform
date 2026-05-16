# Divinheal Data Platform

Standalone data platform for collecting, validating, reviewing, and exporting source-backed medical tourism data for Divinheal.

It is intended to support multi-destination medical tourism data, including visa rules, patient country profiles, hospitals, doctors, flights, FAQs, testimonials/reviews, and future cost/success-rate datasets.

## Core principles

- Source-backed data only.
- No silent fallback or fake/stub values in final outputs.
- Raw source responses are stored before normalization.
- Missing or failed data is tracked explicitly.
- AI may assist extraction, cleanup, classification, or deduplication, but AI is not a source of truth.
- Postgres is used for structured metadata and records.
- Cloudflare R2 will be used for raw dumps and exported artifacts.
- CSV schemas in `configs/schemas/` are treated as reference schemas unless explicitly changed.

## Current status

Project initialized. No production scraper has been implemented yet.