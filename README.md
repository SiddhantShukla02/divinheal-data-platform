# DivinHeal Data Platform

Source-backed data platform for medical-tourism research. Collects hospital, treatment and country-level data from multiple sources, stores raw responses before normalisation, and treats AI as an extraction assistant rather than a source of truth.

## Architecture

```
sources/          scrape or fetch raw data from each provider
  scraper_c.py      Playwright scraper — CureMeAbroad hospital directory
  vaidam/           Vaidam hospital listings (country-level)
  medigence_hospitals.py
  exchange_rates.py, world_bank_population.py, ai_outbound_medical_travel.py

pipelines/        transform and combine source data
  patient_country_destination_profiles.py

core/             shared utilities — run context, status tracking, settings
configs/          per-source YAML configs
schemas/          reference and target CSV schemas
tests/            unit tests for sources, pipelines and core modules
notebooks/        exploratory / reference notebooks
docs/             architecture decisions, setup guide, next steps
```

## Key components

### Playwright hospital scraper (`sources/scraper_c.py`)

Scrapes the CureMeAbroad hospital directory using Playwright (Chromium):

1. Loads the listing page and scrolls through the infinite-scroll feed until every card appears.
2. Extracts each card's name, description and URL.
3. Opens each hospital's detail page and pulls location, payment methods, accessibility features, highlights and room types.
4. Saves the full dataset as structured JSON.

Runs headless by default. Includes per-hospital error handling so one failed detail page does not abort the run.

### Other data sources

- **Vaidam** — hospital listings by country
- **Medigence** — hospital metadata
- **Exchange rates, World Bank population, AI outbound medical travel** — reference datasets for country profiles

### Pipelines

- **Patient-country destination profiles** — merges hospital, population and travel data into per-country profiles

## Setup

```bash
# requires Python 3.11+
pip install -e ".[dev]"
playwright install chromium

# run the hospital scraper
python -m divinheal_data.sources.scraper_c

# run tests
pytest
```

## Design principles

- **Source-backed**: raw responses are stored before any transformation; every derived field traces back to a raw value.
- **Explicit failure tracking**: missing and failed data is recorded, not silently dropped.
- **AI-assisted, not AI-sourced**: LLMs help extract and clean data; they are never the primary source.

## Status

Active development. The Playwright scraper, exchange-rate and World Bank sources, and the country-profile pipeline are functional. Vaidam and Medigence integrations are in progress. Two detail-page extractors (accreditations, full address) are stubbed pending site-structure confirmation.
