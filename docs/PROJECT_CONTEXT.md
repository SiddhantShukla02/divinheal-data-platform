# Project Context

This repository is the standalone Divinheal data platform.

It is separate from the old Divinheal blog/content pipeline and should not depend on that codebase.

## Goal

Build a source-backed data platform for medical tourism data across multiple destination countries.

The platform should support collecting, storing, normalizing, validating, reviewing, and exporting data for datasets such as:

- visa rules
- patient country profiles
- hospitals
- doctors
- flights
- FAQs
- testimonials/reviews
- future cost and success-rate datasets

## Current stage

The project is at initial setup.

No production scrapers or pipelines have been implemented yet.

Uploaded CSV files in `configs/schemas/` are treated as reference schemas for now.

The notebook in `notebooks/reference/` is reference material only. It should not be copied directly into production structure without review.

## Core principles

- Source-backed data only.
- AI is not a source of truth.
- AI may assist with extraction, cleanup, classification, deduplication, or normalization only when the underlying source is real and traceable.
- Raw source responses should be stored before normalization.
- Missing data should be tracked explicitly.
- Failed source attempts should be tracked explicitly.
- Stub, fake, or silent fallback data must not enter final outputs.
- Sensitive/high-impact data such as visa rules, doctor credentials, hospital accreditations, and testimonials should require careful review.
- The platform should support multiple destination countries, not only India.