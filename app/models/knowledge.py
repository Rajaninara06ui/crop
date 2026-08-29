from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.database import Base


class AdvisoryResult(Base):
    __tablename__ = "advisory_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), index=True)
    possible_issue: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    message: Mapped["Message"] = relationship(back_populates="advisory_results")
    sources: Mapped[list["Source"]] = relationship(back_populates="advisory_result", cascade="all, delete-orphan")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    advisory_result_id: Mapped[int] = mapped_column(ForeignKey("advisory_results.id", ondelete="CASCADE"), index=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str | None] = mapped_column(String(500), nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)

    advisory_result: Mapped["AdvisoryResult"] = relationship(back_populates="sources")
