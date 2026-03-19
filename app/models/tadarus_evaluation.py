from sqlalchemy import Column, Integer, Text, JSON, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.db.base import Base

class TadarusEvaluation(Base):
    __tablename__ = "tadarus_evaluations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    surah = Column(Integer, nullable=False)
    ayah = Column(Integer, nullable=False)

    score_final = Column(Integer, nullable=False)
    score_ayat = Column(Integer, nullable=False)
    score_audio = Column(Integer, nullable=False)

    asr_user = Column(Text)
    asr_ref = Column(Text)

    issues = Column(JSON)
    suggestions = Column(JSON)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "surah", "ayah"),
    )
