"""
University Management ORM Models.
Defines Courses, FacultyCourseAssignments, CourseEnrollments, Labs, and LabPracticals.
Implements secure university lab structure for LabOS Sentinel.
"""

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Course(Base):
    """
    Academic Course or Subject representation.
    """
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(50), unique=True, index=True, nullable=True)
    name = Column(String(255), nullable=False)
    program = Column(String(100), nullable=False, default="General")
    year_of_study = Column(String(30), nullable=False, default="1st Year")
    description = Column(Text, nullable=True)
    semester = Column(String(50), nullable=False)  # e.g., "Fall 2026", "Semester 1"
    academic_year = Column(String(50), nullable=True)  # e.g., "2026-2027"
    is_active = Column(Boolean, nullable=False, default=True)
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
    creator = relationship("User", foreign_keys=[created_by])
    faculty_assignments = relationship(
        "FacultyCourseAssignment",
        back_populates="course",
        cascade="all, delete-orphan",
    )
    enrollments = relationship(
        "CourseEnrollment",
        back_populates="course",
        cascade="all, delete-orphan",
    )
    labs = relationship(
        "Lab",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Lab.display_order",
    )

    def __repr__(self) -> str:
        return f"<Course id={self.id} code='{self.code}' name='{self.name}'>"


class FacultyCourseAssignment(Base):
    """
    Explicit assignment of a faculty member to manage a course.
    """
    __tablename__ = "faculty_course_assignments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    course_id = Column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    faculty_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    assigned_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("course_id", "faculty_id", name="uq_course_faculty_assignment"),
    )

    # Relationships
    course = relationship("Course", back_populates="faculty_assignments")
    faculty = relationship("User", foreign_keys=[faculty_id])
    assigner = relationship("User", foreign_keys=[assigned_by])

    def __repr__(self) -> str:
        return f"<FacultyCourseAssignment id={self.id} course_id={self.course_id} faculty_id={self.faculty_id}>"


class CourseEnrollment(Base):
    """
    Student membership / enrollment in an academic course.
    """
    __tablename__ = "course_enrollments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    course_id = Column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enrolled_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    status = Column(String(50), nullable=False, default="ENROLLED")

    __table_args__ = (
        UniqueConstraint("course_id", "student_id", name="uq_course_student_enrollment"),
    )

    # Relationships
    course = relationship("Course", back_populates="enrollments")
    student = relationship("User", foreign_keys=[student_id])

    def __repr__(self) -> str:
        return f"<CourseEnrollment id={self.id} course_id={self.course_id} student_id={self.student_id}>"


class Lab(Base):
    """
    Practical laboratory collection belonging to a course.
    """
    __tablename__ = "labs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    course_id = Column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    display_order = Column(Integer, nullable=False, default=0)
    is_published = Column(Boolean, nullable=False, default=False)
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
    course = relationship("Course", back_populates="labs")
    creator = relationship("User", foreign_keys=[created_by])
    practicals = relationship(
        "LabPractical",
        back_populates="lab",
        cascade="all, delete-orphan",
        order_by="LabPractical.sequence_number",
    )

    def __repr__(self) -> str:
        return f"<Lab id={self.id} course_id={self.course_id} title='{self.title}'>"


class LabPractical(Base):
    """
    One ordered practical inside a lab, referencing an authoritative coding question.
    """
    __tablename__ = "lab_practicals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    lab_id = Column(
        Integer,
        ForeignKey("labs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        Integer,
        ForeignKey("questions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=True)  # Optional display override
    instructions = Column(Text, nullable=True)  # Optional practical instructions override
    sequence_number = Column(Integer, nullable=False, default=1)
    is_required = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default='true', index=True)
    passing_threshold = Column(Float, nullable=False, default=100.0, server_default="100.0")
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

    __table_args__ = (
        UniqueConstraint("lab_id", "sequence_number", name="uq_lab_practical_sequence"),
        UniqueConstraint("lab_id", "question_id", name="uq_lab_practical_question"),
    )

    # Relationships
    lab = relationship("Lab", back_populates="practicals")
    question = relationship("Question")
    submissions = relationship(
        "Submission",
        back_populates="practical",
    )

    @property
    def effective_title(self) -> str:
        if self.title and self.title.strip():
            return self.title.strip()
        if self.question and getattr(self.question, "title", None):
            return self.question.title
        return "Practical"

    def __repr__(self) -> str:
        return f"<LabPractical id={self.id} lab_id={self.lab_id} q_id={self.question_id} seq={self.sequence_number} threshold={self.passing_threshold}>"
