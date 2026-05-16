# Schema Notes

This file tracks schema observations, concerns, and proposed future changes.

The CSV files in `configs/schemas/` are currently treated as reference schemas. Do not modify them directly unless explicitly instructed.

## Current schema files

- `01_visa_rules.csv`
- `02_patient_countries.csv`
- `03_hospitals.csv`
- `04_doctors.csv`
- `06_flights.csv`
- `07_testimonials.csv`
- `08_faqs.csv`

Cost and success-rate schemas are intentionally excluded for now because that work is being handled separately.

## General concern: multi-destination support

The platform must support multiple destination countries, not only India.

Many schemas may need a `destination_country_slug` or similar destination-level field so that records can be scoped correctly.

This is especially important for:

- visa rules
- hospitals
- doctors
- flights
- FAQs
- testimonials/reviews

## Visa rules

Current concern:

Visa rules should be modeled as origin country × destination country.

For example:

```text
Bangladesh → India
Bangladesh → Turkey
Bangladesh → Thailand