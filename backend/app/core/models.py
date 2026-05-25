import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    transcript: Mapped[str] = mapped_column(Text, comment="Raw transcription text")

    # Extracted fields
    part_name: Mapped[str] = mapped_column(String(255), index=True)
    part_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ata_chapter: Mapped[str | None] = mapped_column(String(50), nullable=True)
    action_performed: Mapped[str] = mapped_column(Text)

    # Validation engine outputs
    validation_status: Mapped[str] = mapped_column(
        String(20),
        comment="Verification compliance checks outcome (PASS / FAIL)",
        index=True,
    )
    validation_issues: Mapped[list[str]] = mapped_column(
        JSONB, default=list, comment="Descriptions of spec mismatch failures"
    )
    references_used: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, comment="AMM vector search reference metadata chunks"
    )
    compliance_parameters: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True, comment="Dynamic compliance parameters parsed from task"
    )
