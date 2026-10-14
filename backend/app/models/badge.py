"""
Badge ORM Model.
Automatically awarded to students upon passing an individual practical.
Guarantees idempotency via unique constraint on (user_id, practical_id).
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Badge(Base):
    """
    Earned practical achievement badge.
    Stores metadata including badge name, type, icon, practical, and subject.
    """
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_id = Column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    practical_id = Column(
        Integer,
        ForeignKey("lab_practicals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    badge_type = Column(
        String(50),
        nullable=False,
        default="PRACTICAL_COMPLETION",
    )
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=False, default="??")

    earned_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    meta = Column(JSON, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "practical_id", name="uq_user_practical_badge"),
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    course = relationship("Course", foreign_keys=[course_id])
    practical = relationship("LabPractical", foreign_keys=[practical_id])

    def __repr__(self) -> str:
        return f"<Badge id={self.id} user_id={self.user_id} name='{self.name}'>"
