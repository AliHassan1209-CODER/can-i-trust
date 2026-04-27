from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class InputType(str, enum.Enum):
    text  = "text"
    url   = "url"
    image = "image"


class Verdict(str, enum.Enum):
    real      = "real"
    fake      = "fake"
    uncertain = "uncertain"


class CheckHistory(Base):
    __tablename__ = "check_history"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"), nullable=False)
    input_type       = Column(Enum(InputType), nullable=False)
    original_input   = Column(Text, nullable=False)       # raw URL or filename
    extracted_text   = Column(Text, nullable=False)       # text passed to model
    verdict          = Column(Enum(Verdict), nullable=False)
    trust_score      = Column(Float, nullable=False)       # 0.0 – 100.0
    confidence       = Column(Float, nullable=False)       # 0.0 – 1.0
    source_score     = Column(Float, nullable=True)
    sentiment_score  = Column(Float, nullable=True)
    language_score   = Column(Float, nullable=True)
    claim_score      = Column(Float, nullable=True)
    model_version    = Column(String(50), default="v1.0")
    processing_ms    = Column(Integer, nullable=True)      # latency tracking
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="checks")

    def __repr__(self):
        return f"<Check id={self.id} verdict={self.verdict} score={self.trust_score}>"
