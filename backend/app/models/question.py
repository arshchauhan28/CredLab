"""
Question & Problem Statement ORM Models.
Defines questions, allowed language relationships, and public examples.
"""

import enum
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class QuestionDifficulty(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class QuestionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    input_format = Column(Text, nullable=True)
    output_format = Column(Text, nullable=True)
    constraints = Column(Text, nullable=True)
    
    difficulty = Column(
        Enum(QuestionDifficulty, native_enum=False),
        nullable=False,
        default=QuestionDifficulty.EASY,
    )
    status = Column(
        Enum(QuestionStatus, native_enum=False),
        nullable=False,
        default=QuestionStatus.DRAFT,
    )

    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    creator = relationship("User", backref="created_questions")
    examples = relationship(
        "QuestionExample",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionExample.display_order",
    )
    languages = relationship(
        "QuestionLanguage",
        back_populates="question",
        cascade="all, delete-orphan",
    )
    test_cases = relationship(
        "TestCase",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="TestCase.display_order",
    )
    submissions = relationship(
        "Submission",
        back_populates="question",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Question id={self.id} slug='{self.slug}' status='{self.status}'>"


class QuestionExample(Base):
    __tablename__ = "question_examples"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    question_id = Column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input = Column(Text, nullable=False)
    output = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)

    # Relationship
    question = relationship("Question", back_populates="examples")

    def __repr__(self) -> str:
        return f"<QuestionExample id={self.id} question_id={self.question_id}>"


class QuestionLanguage(Base):
    __tablename__ = "question_languages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    question_id = Column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language = Column(String(50), nullable=False)  # e.g., 'python', 'cpp', 'java', 'javascript'

    __table_args__ = (
        UniqueConstraint("question_id", "language", name="uq_question_language"),
    )

    # Relationship
    question = relationship("Question", back_populates="languages")

    def __repr__(self) -> str:
        return f"<QuestionLanguage question_id={self.question_id} language='{self.language}'>"
