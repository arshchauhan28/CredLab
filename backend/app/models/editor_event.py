"""
Editor Activity Event ORM Model (Chunk 6).
Defines schema for capturing editor activities, keystroke counts,
and anti-copy/paste deterrence events without capturing source code or clipboard text.
"""

import enum
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, JSON, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class EditorEventType(str, enum.Enum):
    TYPE = "TYPE"
    DELETE = "DELETE"
    PASTE_ATTEMPT = "PASTE_ATTEMPT"
    COPY_ATTEMPT = "COPY_ATTEMPT"
    CUT_ATTEMPT = "CUT_ATTEMPT"
    DROP_ATTEMPT = "DROP_ATTEMPT"


class EditorEvent(Base):
    """
    Represents an editor activity event captured during a coding assessment.
    Stores metadata only (character delta, timestamps, event type) to preserve privacy.
    Strictly forbids storing source code or clipboard contents.
    """
    __tablename__ = "editor_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        Integer,
        ForeignKey("questions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type = Column(String(50), nullable=False, index=True)
    event_timestamp = Column(DateTime(timezone=True), nullable=False)
    language = Column(String(50), nullable=True)
    session_id = Column(String(100), nullable=True, index=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", backref="editor_events")
    question = relationship("Question", backref="editor_events")

    def __repr__(self) -> str:
        return f"<EditorEvent id={self.id} user_id={self.user_id} type='{self.event_type}'>"
