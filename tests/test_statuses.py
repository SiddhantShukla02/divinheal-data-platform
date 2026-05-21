# -----------------------------------------------------------------------------
# STATUS CONSTANT TESTS
# -----------------------------------------------------------------------------
# PURPOSE:
#   Verifies that shared status enums expose the expected stable string values.
#
# INPUT:
#   SourceAttemptStatus and RecordStatus from divinheal_data.core.statuses.
#
# PROCESS:
#   - Checks source-attempt status values.
#   - Checks important record lifecycle status values.
#   - Confirms enum values behave like strings.
#
# OUTPUT:
#   Passing tests for the shared status vocabulary.
#
# NOTES:
#   - These tests protect against accidental status renames that could break
#     database rows, exports, or downstream filters later.
# -----------------------------------------------------------------------------

from divinheal_data.core.statuses import RecordStatus, SourceAttemptStatus


def test_source_attempt_status_values() -> None:
    assert SourceAttemptStatus.SUCCESS == "success"
    assert SourceAttemptStatus.FAILED == "failed"


def test_record_status_values() -> None:
    assert RecordStatus.CANDIDATE == "candidate"
    assert RecordStatus.VERIFIED == "verified"
    assert RecordStatus.NEEDS_REVIEW == "needs_review"
    assert RecordStatus.MISSING_SOURCE == "missing_source"
    assert RecordStatus.SOURCE_FAILED == "source_failed"
    assert RecordStatus.STALE == "stale"
    assert RecordStatus.CONFLICTING_SOURCES == "conflicting_sources"
    assert RecordStatus.REJECTED == "rejected"
    assert RecordStatus.APPROVED == "approved"


def test_statuses_are_strings() -> None:
    assert isinstance(SourceAttemptStatus.SUCCESS, str)
    assert isinstance(RecordStatus.NEEDS_REVIEW, str)