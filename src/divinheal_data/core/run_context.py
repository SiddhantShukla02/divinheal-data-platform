# -----------------------------------------------------------------------------
# RUN CONTEXT MODEL
# -----------------------------------------------------------------------------
# PURPOSE:
#   Defines the metadata object that identifies a single pipeline/source run.
#
# INPUT:
#   - pipeline_name: stable name of the pipeline being executed
#   - run_id: optional caller-provided ID; generated automatically if omitted
#   - started_at: optional caller-provided timestamp; generated automatically if omitted
#   - metadata: optional extra run details for debugging or filtering
#
# PROCESS:
#   - Creates a run context with a unique run ID.
#   - Stores a timezone-aware UTC start timestamp.
#   - Keeps optional metadata separate from core run identity fields.
#
# OUTPUT:
#   - RunContext dataclass
#
# NOTES:
#   - This does not write to Postgres yet.
#   - DB persistence will be added later after the base model is stable.
# -----------------------------------------------------------------------------

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


@dataclass(frozen=True)
class RunContext:
    """Runtime identity and metadata for one pipeline execution."""

    pipeline_name: str
    run_id: str = field(default_factory=lambda: uuid4().hex)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, str] = field(default_factory=dict)

    def storage_prefix(self) -> str:
        """Return a stable storage prefix for artifacts created by this run."""

        return f"{self.pipeline_name}/{self.run_id}"