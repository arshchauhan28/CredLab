"""
User ORM Model.

Defines application users, enrollment-number identity, and role-based access
control while preserving existing academic profile fields.
"""

import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    FACULTY = "FACULTY"
    ADMIN = "ADMIN"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            normalized = value.upper()
            for member in cls:
                if member.value == normalized:
                    return member
        return None


class ApprovalStatus(str, enum.Enum):
    """Registration approval state for faculty and administrator accounts."""
    PENDING = "PENDING"       # Awaiting review
    APPROVED = "APPROVED"     # Access granted
    REJECTED = "REJECTED"     # Access denied


class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
    )

    name = Column(String(100), nullable=False)

    email = Column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    password_hash = Column(String(255), nullable=False)

    role = Column(
        Enum(UserRole, native_enum=False),
        nullable=False,
        default=UserRole.STUDENT,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    # New authentication fields.
    # Nullable initially to preserve compatibility with existing accounts.
    enrollment_number = Column(
        String(10),
        unique=True,
        index=True,
        nullable=True,
    )

    admin_job_role = Column(
        String(100),
        nullable=True,
    )

    # Existing student academic profile fields.
    student_id_number = Column(
        String(50),
        unique=True,
        index=True,
        nullable=True,
    )

    academic_course = Column(
        String(100),
        nullable=True,
    )

    academic_year = Column(
        String(50),
        nullable=True,
    )

    semester = Column(
        String(50),
        nullable=True,
    )

    year_of_study = Column(
        String(30),
        nullable=True,
    )

    # Approval status for faculty and admin accounts.
    # Students are always APPROVED on registration.
    # Existing accounts without this column default to APPROVED (see migration).
    approval_status = Column(
        String(30),
        nullable=False,
        default="APPROVED",
        server_default="APPROVED",
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

    # Existing relationships must remain intact.
    submissions = relationship(
        "Submission",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def profile_completed(self) -> bool:
        if self.role != UserRole.STUDENT:
            return True

        return bool(
            self.student_id_number
            and self.academic_course
            and self.academic_year
            and self.semester
            and self.year_of_study
        )

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_faculty(self) -> bool:
        return self.role == UserRole.FACULTY

    @property
    def is_student(self) -> bool:
        return self.role == UserRole.STUDENT

    def __repr__(self) -> str:
        return (
            f"<User id={self.id} "
            f"email='{self.email}' "
            f"role='{self.role}'>"
        )