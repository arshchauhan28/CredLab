"""
Registration Approval ORM Model.

Records faculty and administrator registration approval decisions.
Used to enforce the approval workflow and provide an audit trail.
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class RegistrationApproval(Base):
    """
    Audit record for a faculty or administrator registration approval decision.
    One record per applicant (upserted on each review action).
    """
    __tablename__ = "registration_approvals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # The user whose registration is being reviewed
    applicant_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # FACULTY or ADMIN
    account_type = Column(String(30), nullable=False)

    # PENDING, APPROVED, REJECTED
    decision = Column(String(30), nullable=False, default="PENDING")

    # The administrator who made the decision (null until reviewed)
    reviewer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    rejection_reason = Column(Text, nullable=True)

    requested_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    applicant = relationship("User", foreign_keys=[applicant_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])

    def __repr__(self) -> str:
        return (
            f"<RegistrationApproval id={self.id} "
            f"applicant_id={self.applicant_id} "
            f"decision='{self.decision}'>"
        )
