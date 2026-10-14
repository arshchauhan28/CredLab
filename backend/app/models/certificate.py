"""
Completion Certificate and Public Key Registry ORM Models.
Defines schemas for tamper-evident, digitally signed university practical completion certificates
and trusted public keys for Ed25519 signature verification.
"""

import uuid
from sqlalchemy import (
    Boolean,
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


class CompletionCertificate(Base):
    """
    Cryptographically signed completion record for a university lab practical or academic subject.
    Guarantees integrity via SHA-256 canonical payload digest and Ed25519 signature.
    """
    __tablename__ = "completion_certificates"

    id = Column(
        String(36),
        primary_key=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    student_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    practical_id = Column(
        Integer,
        ForeignKey("lab_practicals.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    submission_id = Column(
        Integer,
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    course_id = Column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    certificate_type = Column(
        String(30),
        nullable=False,
        default="PRACTICAL",
        index=True,
    )

    schema_version = Column(String(20), nullable=False, default="1.0")
    issuer = Column(String(100), nullable=False, default="LabOS Sentinel")
    algorithm = Column(String(50), nullable=False, default="ED25519-SHA256")
    key_id = Column(String(100), nullable=False, index=True)

    # Canonical payload (JSON structure)
    payload = Column(JSON, nullable=False)

    # Cryptographic proof fields
    payload_digest = Column(String(64), nullable=False)  # 64-char hex SHA-256
    signature = Column(String(128), nullable=False)       # 128-char hex Ed25519 signature

    # Lifecycle status: ACTIVE, REVOKED, SUPERSEDED
    status = Column(String(20), nullable=False, default="ACTIVE", index=True)

    # Timestamps
    completed_at = Column(DateTime(timezone=True), nullable=False)
    issued_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("student_id", "practical_id", name="uq_certificate_student_practical"),
    )

    # Relationships
    student = relationship("User", foreign_keys=[student_id])
    practical = relationship("LabPractical", foreign_keys=[practical_id])
    submission = relationship("Submission", foreign_keys=[submission_id])
    course = relationship("Course", foreign_keys=[course_id])

    def __repr__(self) -> str:
        return (
            f"<CompletionCertificate id={self.id} student_id={self.student_id} "
            f"practical_id={self.practical_id} course_id={self.course_id} "
            f"type='{self.certificate_type}' status='{self.status}'>"
        )


class CertificateSigningKey(Base):
    """
    Public key registry storing trusted Ed25519 public keys for signature verification.
    NEVER stores private keys. Used to verify historical and active certificates after key rotation.
    """
    __tablename__ = "certificate_signing_keys"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    key_id = Column(String(100), unique=True, index=True, nullable=False)
    public_key_hex = Column(String(64), nullable=False)  # 32-byte Ed25519 public key as 64 hex chars
    algorithm = Column(String(50), nullable=False, default="ED25519-SHA256")
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<CertificateSigningKey key_id='{self.key_id}' active={self.is_active}>"


class CertificateApprovalRequest(Base):
    """A student requests a lab-completion certificate; assigned faculty must approve it."""
    __tablename__ = "certificate_approval_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    lab_id = Column(Integer, ForeignKey("labs.id", ondelete="CASCADE"), nullable=False, index=True)
    practical_id = Column(Integer, ForeignKey("lab_practicals.id", ondelete="CASCADE"), nullable=False, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(30), nullable=False, default="PENDING", index=True)
    reviewed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_note = Column(Text, nullable=True)
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("student_id", "lab_id", name="uq_certificate_request_student_lab"),)

    student = relationship("User", foreign_keys=[student_id])
    lab = relationship("Lab", foreign_keys=[lab_id])
    practical = relationship("LabPractical", foreign_keys=[practical_id])
    submission = relationship("Submission", foreign_keys=[submission_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])


class SubjectCertificateRequest(Base):
    """
    A student requests a subject-level completion certificate after completing
    all required practicals in the subject; authorized faculty must approve it.
    """
    __tablename__ = "subject_certificate_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    course_id = Column(
        Integer,
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(30), nullable=False, default="PENDING", index=True)
    reviewed_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_note = Column(Text, nullable=True)
    requested_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "student_id",
            "course_id",
            name="uq_subject_cert_request_student_course",
        ),
    )

    student = relationship("User", foreign_keys=[student_id])
    course = relationship("Course", foreign_keys=[course_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self) -> str:
        return (
            f"<SubjectCertificateRequest id={self.id} student_id={self.student_id} "
            f"course_id={self.course_id} status='{self.status}'>"
        )
