# Architecture

This project is a source-backed data platform for Divinheal medical tourism data.

The platform is not a single scraper. It is a system for collecting, storing, extracting, normalizing, validating, reviewing, approving, and exporting data from multiple sources.

## Core data flow

```text
Dataset goal / input config
  ↓
Source registry
  ↓
Source attempts
  ↓
Raw artifact storage
  ↓
Extraction / parsing
  ↓
Source-level normalized records
  ↓
Dataset mapping
  ↓
Dataset-level candidate records
  ↓
Validation + quality scoring
  ↓
Review queue where needed
  ↓
Approved records
  ↓
Exports / application-facing tables