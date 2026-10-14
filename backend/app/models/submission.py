"""
Submission, Trusted Test Cases, and Automated Grading ORM Models.
Defines schemas for permanent candidate submissions, authoritative backend test cases,
and individual test execution results.
"""

import enum
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class SubmissionStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    ACCEPTED = "ACCEPTED"
    WRONG_ANSWER = "WRONG_ANSWER"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    COMPILATION_ERROR = "COMPILATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class TestCase(Base):
    """
    Authoritative backend-owned test cases for evaluating programming problems.
    Supports public sample cases and protected hidden assessment test cases.
    """
    __test__ = False
    __tablename__ = "test_cases"


    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    question_id = Column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=False)
    is_hidden = Column(Boolean, nullable=False, default=False)
    display_order = Column(Integer, nullable=False, default=0)
    weight = Column(Float, nullable=False, default=1.0)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    question = relationship("Question", back_populates="test_cases")
    results = relationship(
        "SubmissionTestResult",
        back_populates="test_case",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<TestCase id={self.id} question_id={self.question_id} is_hidden={self.is_hidden}>"


class Submission(Base):
    """
    Permanent candidate submission record storing code snapshot, aggregate grading outcome,
    metrics, and timestamps.
    """
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    practical_id = Column(
        Integer,
        ForeignKey("lab_practicals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    language = Column(String(50), nullable=False)
    source_code = Column(Text, nullable=False)
    
    status = Column(
        Enum(SubmissionStatus, native_enum=False),
        nullable=False,
        default=SubmissionStatus.PENDING,
        index=True,
    )
    total_test_cases = Column(Integer, nullable=False, default=0)
    passed_test_cases = Column(Integer, nullable=False, default=0)
    score = Column(Float, nullable=False, default=0.0)
    
    execution_time_ms = Column(Integer, nullable=True)
    memory_kb = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="submissions")
    question = relationship("Question", back_populates="submissions")
    practical = relationship("LabPractical", back_populates="submissions")
    test_results = relationship(
        "SubmissionTestResult",
        back_populates="submission",
        cascade="all, delete-orphan",
        order_by="SubmissionTestResult.id",
    )

    def __repr__(self) -> str:
        return f"<Submission id={self.id} user_id={self.user_id} q_id={self.question_id} prac_id={self.practical_id} status='{self.status}'>"


class SubmissionTestResult(Base):
    """
    Individual test-case grading outcome record linked to a submission.
    """
    __tablename__ = "submission_test_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    submission_id = Column(
        Integer,
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_case_id = Column(
        Integer,
        ForeignKey("test_cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(String(50), nullable=False)
    passed = Column(Boolean, nullable=False, default=False)
    execution_time_ms = Column(Integer, nullable=True)
    memory_kb = Column(Integer, nullable=True)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    submission = relationship("Submission", back_populates="test_results")
    test_case = relationship("TestCase", back_populates="results")

    def __repr__(self) -> str:
        return f"<SubmissionTestResult id={self.id} sub_id={self.submission_id} passed={self.passed}>"
