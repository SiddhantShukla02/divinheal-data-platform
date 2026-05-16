# -----------------------------------------------------------------------------
# RUN CONTEXT TESTS
# -----------------------------------------------------------------------------
# PURPOSE:
#   Verifies that RunContext creates stable run metadata for pipeline executions.
#
# INPUT:
#   RunContext from divinheal_data.core.run_context.
#
# PROCESS:
#   - Creates run contexts with automatic and manual values.
#   - Checks generated run IDs and timestamps.
#   - Checks storage prefix formatting.
#   - Confirms metadata defaults are isolated per instance.
#
# OUTPUT:
#   Passing tests for run identity and storage-prefix behavior.
#
# NOTES:
#   - These tests protect artifact paths and future DB run records from unstable
#     run identity behavior.
# -----------------------------------------------------------------------------

from datetime import UTC, datetime

from divinheal_data.core.run_context import RunContext


def test_run_context_generates_defaults() -> None:
    context = RunContext(pipeline_name="patient_country_basics")

    assert context.pipeline_name == "patient_country_basics"
    assert len(context.run_id) == 32
    assert context.started_at.tzinfo == UTC
    assert context.metadata == {}


def test_run_context_accepts_manual_values() -> None:
    started_at = datetime(2026, 5, 16, 12, 0, tzinfo=UTC)

    context = RunContext(
        pipeline_name="patient_country_basics",
        run_id="manual_run_id",
        started_at=started_at,
        metadata={"environment": "test"},
    )

    assert context.pipeline_name == "patient_country_basics"
    assert context.run_id == "manual_run_id"
    assert context.started_at == started_at
    assert context.metadata == {"environment": "test"}


def test_storage_prefix_uses_pipeline_name_and_run_id() -> None:
    context = RunContext(
        pipeline_name="patient_country_basics",
        run_id="abc123",
    )

    assert context.storage_prefix() == "patient_country_basics/abc123"


def test_metadata_defaults_are_isolated() -> None:
    first = RunContext(pipeline_name="first")
    second = RunContext(pipeline_name="second")

    assert first.metadata is not second.metadata