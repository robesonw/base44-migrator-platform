from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Enum, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
from app.core.workflow import JobStage

class MigrationJob(Base):
    __tablename__ = "migration_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    source_repo_url: Mapped[str] = mapped_column(Text, nullable=False)
    target_repo_url: Mapped[str] = mapped_column(Text, nullable=False)

    backend_stack: Mapped[str] = mapped_column(String(20), nullable=False)
    db_stack: Mapped[str] = mapped_column(String(20), nullable=False)
    commit_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="pr")

    stage: Mapped[JobStage] = mapped_column(Enum(JobStage), default=JobStage.CLONE_SOURCE, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="QUEUED", nullable=False)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifacts: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
