"""
Authorized Enrollment ORM Model.

Controls which enrollment numbers may register for the platform.
Each enrollment number can be claimed by at most one user.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.user import UserRole


class AuthorizedEnrollment(Base):
    __tablename__ = "authorized_enrollments"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
        autoincrement=True,
    )

    enrollment_number = Column(
        String(10),
        unique=True,
        index=True,
        nullable=False,
    )

    expected_role = Column(
        Enum(UserRole, native_enum=False),
        nullable=False,
    )

    # Required for ADMIN enrollment authorizations. NULL legacy values remain
    # deliberately unprovisioned and cannot be used for administrator signup.
    admin_job_role = Column(String(100), nullable=True, index=True)

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    # Optional association with an existing course.
    # Primarily useful for student enrollment authorization.
    course_id = Column(
        Integer,
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # A NULL value means the enrollment number has not been claimed.
    claimed_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        unique=True,
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    course = relationship("Course")

    claimed_by_user = relationship(
        "User",
        foreign_keys=[claimed_by_user_id],
    )

    def __repr__(self) -> str:
        return (
            f"<AuthorizedEnrollment "
            f"id={self.id} "
            f"enrollment_number='{self.enrollment_number}' "
            f"expected_role='{self.expected_role}'>"
        )