# Architecture Decisions

This file records important project decisions so future chats, Codex sessions, and contributors do not lose context.

## 2026-05-16 — Standalone repository

Decision: This project lives in a new standalone repository named `divinheal-data-platform`.

Reason: The medical tourism data platform is larger and more important than the old blog/content pipeline. It should not inherit old pipeline structure, assumptions, or technical debt.

## 2026-05-16 — Local Postgres first

Decision: Use local Postgres for v1 development.

Reason: The platform will eventually need relational data, JSONB candidate records, constraints, indexes, upserts, review workflows, and likely cloud Postgres deployment. Starting with Postgres locally reduces migration friction compared to starting with SQLite.

Implementation note: Local Postgres may be installed directly on the machine or run through Docker Compose. The application should rely on `DATABASE_URL`, not on a specific local setup method.

Future note: Production can use AWS RDS Postgres, Neon, Supabase, Railway, or another managed Postgres provider. The app should use a standard `DATABASE_URL` so the provider can be changed later.

## 2026-05-16 — R2 for artifact storage

Decision: Use a separate Cloudflare R2 bucket for raw dumps, normalized exports, error files, review queues, and schema snapshots.

Reason: Raw source responses and exports can become bulky. Object storage is better than storing large blobs directly in the DB.

Current implementation note: v1 should support local storage first using the same logical key structure that R2 will later use.

## 2026-05-16 — Source-backed data only

Decision: Final data must be traceable to real sources.

Reason: Medical tourism data can affect business trust and user decisions. Stub, fake, guessed, or silent fallback values can become dangerous and painful to clean later.

## 2026-05-16 — AI is not a source of truth

Decision: AI may assist extraction, cleanup, classification, deduplication, and normalization, but it must not be treated as the source of truth.

Reason: AI-generated facts are not reliable enough for final data. Every important value should point back to a source URL, source file, or manual review record.

## 2026-05-16 — Raw before normalized

Decision: Store raw source responses before transforming them into normalized records.

Reason: This makes failures debuggable and allows extraction logic to be rerun without refetching source data.

## 2026-05-16 — Explicit missing/error records

Decision: Missing data and source failures must be recorded explicitly.

Reason: The system should not hide failures inside logs or silently fill defaults. Failed fields should produce structured records with status, failure reason, source attempted, and next action.

## 2026-05-16 — Multi-destination support

Decision: The platform should support multiple destination countries, not only India.

Reason: Divinheal plans destination expansion. Many datasets need destination-level fields or relations, especially visa rules, hospitals, doctors, FAQs, testimonials, and flights.

## 2026-05-16 — Start simple with folder structure

Decision: Start with a lean folder structure: `core`, `sources`, and `pipelines`.

Reason: Overbuilding folders too early creates complexity. Source-specific adapters and dataset pipelines can be split further later if the codebase grows.