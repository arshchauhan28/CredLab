"""
SQLAlchemy ORM Models Package.

Exports all database entity models for application use and Alembic migrations.
"""

from app.core.database import Base

from app.models.user import User, UserRole, ApprovalStatus
from app.models.authorized_enrollment import AuthorizedEnrollment
from app.models.registration_approval import RegistrationApproval

from app.models.question import (
    Question,
    QuestionExample,
    QuestionLanguage,
    QuestionDifficulty,
    QuestionStatus,
)

from app.models.editor_event import EditorEvent, EditorEventType

from app.models.submission import (
    TestCase,
    Submission,
    SubmissionStatus,
    SubmissionTestResult,
)

from app.models.university import (
    Course,
    FacultyCourseAssignment,
    CourseEnrollment,
    Lab,
    LabPractical,
)

from app.models.badge import Badge
from app.models.certificate import (
    CompletionCertificate,
    CertificateSigningKey,
    CertificateApprovalRequest,
    SubjectCertificateRequest,
)

__all__ = [
    "Base",
    "User",
    "UserRole",
    "AuthorizedEnrollment",
    "Question",
    "QuestionExample",
    "QuestionLanguage",
    "QuestionDifficulty",
    "QuestionStatus",
    "EditorEvent",
    "EditorEventType",
    "TestCase",
    "Submission",
    "SubmissionStatus",
    "SubmissionTestResult",
    "Course",
    "FacultyCourseAssignment",
    "CourseEnrollment",
    "Lab",
    "LabPractical",
    "CompletionCertificate",
    "CertificateSigningKey",
    "CertificateApprovalRequest",
    "SubjectCertificateRequest",
    "Badge",
    "RegistrationApproval",
    "ApprovalStatus",
]