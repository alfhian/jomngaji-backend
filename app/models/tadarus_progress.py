from sqlalchemy import Column, Integer, Float, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.db.base import Base

class TadarusProgress(Base):
    __tablename__ = "tadarus_progress"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    surah = Column(Integer, nullable=False)

    completed_ayah = Column(Integer, default=0)
    total_ayah = Column(Integer, nullable=False)
    average_score = Column(Float, default=0)

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "surah"),
    )
