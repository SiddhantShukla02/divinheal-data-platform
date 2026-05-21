# -----------------------------------------------------------------------------
# SHARED STATUS CONSTANTS
# -----------------------------------------------------------------------------
# PURPOSE:
#   Defines the shared status vocabulary used across source attempts, candidate
#   records, review records, approved records, and exports.
#
# INPUT:
#   None. This module only exposes enums/constants for other modules to import.
#
# PROCESS:
#   - Defines source-attempt statuses separately from data-record statuses.
#   - Uses StrEnum so statuses behave like strings when saved to JSON, CSV, or DB.
#   - Centralizes status values so pipelines do not invent inconsistent strings.
#
# OUTPUT:
#   - SourceAttemptStatus
#   - RecordStatus
#
# NOTES:
#   - Requires Python 3.11+ because StrEnum is used.
#   - Add new statuses here intentionally; do not create ad-hoc status strings
#     inside source adapters or pipelines.
# -----------------------------------------------------------------------------

from enum import StrEnum


class SourceAttemptStatus(StrEnum):
    """Status values for attempts to fetch or access a source."""

    SUCCESS = "success"
    FAILED = "failed"


class RecordStatus(StrEnum):
    """Status values for normalized, candidate, review, and approved records."""

    CANDIDATE = "candidate"
    VERIFIED = "verified"
    NEEDS_REVIEW = "needs_review"
    MISSING_SOURCE = "missing_source"
    SOURCE_FAILED = "source_failed"
    STALE = "stale"
    CONFLICTING_SOURCES = "conflicting_sources"
    REJECTED = "rejected"
    APPROVED = "approved"