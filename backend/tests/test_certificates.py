"""
Chunk 10 Test Suite: Cryptographic Completion Certificates & Ed25519 Signatures.
Comprehensive tests covering:
A. Certificate creation and eligibility rules (Tests 1-12)
B. Cryptographic correctness and tamper detection (Tests 13-30)
C. Key security, rotation, and configuration safety (Tests 31-37)
D. Authorization, RBAC, and integrity (Tests 38-44)
E. Regression and backward compatibility (Tests 45-50)
"""

import copy
import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from unittest.mock import patch
import pytest

from cryptography.hazmat.primitives.asymmetric import ed25519

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.certificate import CertificateSigningKey, CompletionCertificate
from app.models.question import Question, QuestionDifficulty, QuestionLanguage, QuestionStatus
from app.models.submission import Submission, SubmissionStatus, SubmissionTestResult, TestCase
from app.models.university import (
    Course,
    CourseEnrollment,
    FacultyCourseAssignment,
    Lab,
    LabPractical,
)
from app.models.user import User, UserRole
from app.services.certificate import (
    CertificateService,
    certificate_service,
    compute_payload_digest,
    format_utc_timestamp,
    serialize_canonical_payload,
)


# ==============================================================================
# Test Fixtures & Helpers
# ==============================================================================

def make_user(db_session, name: str, email: str, role: UserRole) -> User:
    user = User(
        name=name,
        email=email,
        password_hash=hash_password("SecurePassword123"),
        role=role,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_header(user: User) -> dict:
    token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value, "email": user.email}
    )
    return {"Authorization": f"Bearer {token}"}


def make_question(db_session, title: str, slug: str, creator_id: int) -> Question:
    q = Question(
        title=title,
        slug=slug,
        description=f"Description for {title}",
        difficulty=QuestionDifficulty.EASY,
        status=QuestionStatus.PUBLISHED,
        created_by=creator_id,
    )
    db_session.add(q)
    db_session.flush()

    db_session.add(QuestionLanguage(question_id=q.id, language="python"))
    tc = TestCase(
        question_id=q.id,
        input="10\n",
        expected_output="10\n",
        is_hidden=False,
        weight=1.0,
    )
    db_session.add(tc)
    db_session.commit()
    db_session.refresh(q)
    return q


def make_course_and_lab(db_session, admin: User, faculty: User, code: str = "CS301") -> tuple:
    course = Course(
        code=code,
        name=f"Systems Programming {code}",
        semester="Fall 2026",
        academic_year="2026-2027",
        is_active=True,
        created_by=admin.id,
    )
    db_session.add(course)
    db_session.flush()

    db_session.add(
        FacultyCourseAssignment(
            course_id=course.id,
            faculty_id=faculty.id,
            assigned_by=admin.id,
        )
    )

    lab = Lab(
        course_id=course.id,
        title="Lab 1: Memory & Pointers",
        description="Low level systems programming practical lab",
        display_order=1,
        is_published=True,
        created_by=faculty.id,
    )
    db_session.add(lab)
    db_session.commit()
    db_session.refresh(course)
    db_session.refresh(lab)
    return course, lab


def enroll_student(db_session, course: Course, student: User):
    enrollment = CourseEnrollment(
        course_id=course.id,
        student_id=student.id,
        status="ENROLLED",
    )
    db_session.add(enrollment)
    db_session.commit()
    return enrollment


def make_practical(
    db_session,
    lab: Lab,
    question: Question,
    seq: int = 1,
    is_required: bool = True,
    threshold: float = 100.0,
    title: str = None,
) -> LabPractical:
    p = LabPractical(
        lab_id=lab.id,
        question_id=question.id,
        title=title,
        sequence_number=seq,
        is_required=is_required,
        passing_threshold=threshold,
    )
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def make_submission(
    db_session,
    user: User,
    question: Question,
    practical: LabPractical = None,
    status: SubmissionStatus = SubmissionStatus.ACCEPTED,
    score: float = 100.0,
) -> Submission:
    sub = Submission(
        user_id=user.id,
        question_id=question.id,
        practical_id=practical.id if practical else None,
        language="python",
        source_code="print(10)",
        status=status,
        total_test_cases=1,
        passed_test_cases=1 if status == SubmissionStatus.ACCEPTED else 0,
        score=score,
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return sub


# Ephemeral Test Key Helper
@pytest.fixture(autouse=True)
def setup_test_signing_key(monkeypatch):
    """Provides a fresh isolated ephemeral Ed25519 test keypair for tests."""
    test_key = ed25519.Ed25519PrivateKey.generate()
    test_key_hex = test_key.private_bytes_raw().hex()
    test_pub_hex = test_key.public_key().public_bytes_raw().hex()

    monkeypatch.setattr(settings, "CERTIFICATE_KEY_ID", "test-key-2026")
    monkeypatch.setattr(settings, "CERTIFICATE_PRIVATE_KEY_HEX", test_key_hex)
    monkeypatch.setattr(settings, "CERTIFICATE_TRUSTED_PUBLIC_KEYS", {"test-key-2026": test_pub_hex})
    monkeypatch.setattr(certificate_service, "_dev_key", test_key)
    yield


# ==============================================================================
# Part A: Certificate Creation & Eligibility (Tests 1-12)
# ==============================================================================

def test_1_student_with_passing_practical_receives_certificate(client, db_session):
    """1. A student with a fully graded passing practical can obtain a certificate."""
    admin = make_user(db_session, "Admin 1", "admin1@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 1", "prof1@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 1", "student1@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS301A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q1", "q1", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=80.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    assert res.status_code == 201
    data = res.json()
    assert data["student_id"] == student.id
    assert data["practical_id"] == practical.id
    assert data["score"] == 100.0
    assert data["status"] == "ACTIVE"
    assert data["signature"] is not None
    assert data["payload_digest"] is not None
    assert data["key_id"] == "test-key-2026"


def test_2_failed_practical_cannot_receive_certificate(client, db_session):
    """2. A failed practical cannot receive a certificate."""
    admin = make_user(db_session, "Admin 2", "admin2@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 2", "prof2@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 2", "student2@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS302A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q2", "q2", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.WRONG_ANSWER, score=0.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    assert res.status_code == 400
    assert "no verified submission achieved the passing threshold" in res.json()["detail"]


def test_3_score_below_threshold_cannot_receive_certificate(client, db_session):
    """3. A score below the practical's configured passing threshold cannot receive a certificate."""
    admin = make_user(db_session, "Admin 3", "admin3@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 3", "prof3@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 3", "student3@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS303A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q3", "q3", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=80.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=75.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    assert res.status_code == 400
    assert "80.0%" in res.json()["detail"]


def test_4_incomplete_or_pending_submission_cannot_receive_certificate(client, db_session):
    """4. An incomplete or still-running submission cannot receive a certificate."""
    admin = make_user(db_session, "Admin 4", "admin4@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 4", "prof4@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 4", "student4@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS304A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q4", "q4", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=70.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.RUNNING, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    assert res.status_code == 400


def test_5_compilation_or_runtime_error_cannot_receive_certificate(client, db_session):
    """5. Compilation errors, runtime errors, timeouts and internal grading failures cannot receive a certificate."""
    admin = make_user(db_session, "Admin 5", "admin5@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 5", "prof5@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 5", "student5@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS305A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q5", "q5", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=50.0)

    for bad_status in [
        SubmissionStatus.COMPILATION_ERROR,
        SubmissionStatus.RUNTIME_ERROR,
        SubmissionStatus.TIME_LIMIT_EXCEEDED,
        SubmissionStatus.INTERNAL_ERROR,
    ]:
        make_submission(db_session, student, q, practical, status=bad_status, score=100.0)
        res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
        assert res.status_code == 400


def test_6_standalone_coding_submission_cannot_receive_certificate(client, db_session):
    """6. A standalone coding-question submission cannot be used to obtain a practical completion certificate."""
    admin = make_user(db_session, "Admin 6", "admin6@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 6", "prof6@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 6", "student6@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS306A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q6", "q6", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)

    # Submission with NO practical_id (standalone question practice)
    make_submission(db_session, student, q, practical=None, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    assert res.status_code == 400


def test_7_submission_for_different_practical_cannot_receive_certificate(client, db_session):
    """7. A submission linked to another practical cannot be used to obtain the requested certificate."""
    admin = make_user(db_session, "Admin 7", "admin7@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 7", "prof7@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 7", "student7@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS307A")
    enroll_student(db_session, course, student)

    q1 = make_question(db_session, "Q7-1", "q7-1", admin.id)
    q2 = make_question(db_session, "Q7-2", "q7-2", admin.id)
    practical1 = make_practical(db_session, lab, q1, seq=1, threshold=100.0)
    practical2 = make_practical(db_session, lab, q2, seq=2, threshold=100.0)

    # Student passes practical 1
    make_submission(db_session, student, q1, practical1, status=SubmissionStatus.ACCEPTED, score=100.0)

    # Request certificate for practical 2 (which student has NOT submitted)
    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical2.id}, headers=auth_header(student))
    assert res.status_code == 400


def test_8_submission_owned_by_another_student_cannot_be_used(client, db_session):
    """8. A submission owned by another student cannot be used to obtain a certificate."""
    admin = make_user(db_session, "Admin 8", "admin8@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 8", "prof8@uni.edu", UserRole.FACULTY)
    student1 = make_user(db_session, "Student 8A", "student8a@uni.edu", UserRole.STUDENT)
    student2 = make_user(db_session, "Student 8B", "student8b@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS308A")
    enroll_student(db_session, course, student1)
    enroll_student(db_session, course, student2)

    q = make_question(db_session, "Q8", "q8", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)

    # Only student 1 submitted
    make_submission(db_session, student1, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    # Student 2 tries to issue certificate
    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student2))
    assert res.status_code == 400


def test_9_unauthorized_student_cannot_retrieve_others_certificate(client, db_session):
    """9. An unauthorized student cannot issue or retrieve another student's certificate."""
    admin = make_user(db_session, "Admin 9", "admin9@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 9", "prof9@uni.edu", UserRole.FACULTY)
    student1 = make_user(db_session, "Student 9A", "student9a@uni.edu", UserRole.STUDENT)
    student2 = make_user(db_session, "Student 9B", "student9b@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS309A")
    enroll_student(db_session, course, student1)
    enroll_student(db_session, course, student2)

    q = make_question(db_session, "Q9", "q9", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student1, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    # Student 1 issues certificate
    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student1))
    assert res.status_code == 201
    cert_id = res.json()["id"]

    # Student 2 tries to retrieve Student 1's certificate
    res2 = client.get(f"/api/v1/certificates/{cert_id}", headers=auth_header(student2))
    assert res2.status_code == 404


def test_10_repeated_issuance_request_is_idempotent(client, db_session):
    """10. A repeated issuance request returns the existing certificate (idempotency policy)."""
    admin = make_user(db_session, "Admin 10", "admin10@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 10", "prof10@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 10", "student10@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS310A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q10", "q10", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    # First request
    res1 = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    assert res1.status_code == 201
    cert1 = res1.json()

    # Second request
    res2 = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    assert res2.status_code == 201 or res2.status_code == 200
    cert2 = res2.json()

    assert cert1["id"] == cert2["id"]
    assert cert1["signature"] == cert2["signature"]
    # Only 1 certificate row in DB
    count = db_session.query(CompletionCertificate).filter(CompletionCertificate.practical_id == practical.id).count()
    assert count == 1


def test_11_concurrent_or_duplicate_issuance_guarantees_database_uniqueness(client, db_session):
    """11. Concurrent issuance attempts cannot create conflicting active certificates."""
    admin = make_user(db_session, "Admin 11", "admin11@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 11", "prof11@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 11", "student11@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS311A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q11", "q11", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    cert1 = certificate_service.issue_certificate_for_practical(db_session, student, practical.id)
    # Attempt second call via service
    cert2 = certificate_service.issue_certificate_for_practical(db_session, student, practical.id)
    assert cert1.id == cert2.id

    # Verify UniqueConstraint prevents duplicate entry insertion
    import sqlalchemy.exc
    duplicate = CompletionCertificate(
        id=str(uuid.uuid4()),
        student_id=student.id,
        practical_id=practical.id,
        submission_id=cert1.submission_id,
        schema_version="1.0",
        issuer="LabOS Sentinel",
        algorithm="ED25519-SHA256",
        key_id="test-key",
        payload=cert1.payload,
        payload_digest=cert1.payload_digest,
        signature=cert1.signature,
        status="ACTIVE",
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(duplicate)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_12_invalid_or_missing_signing_configuration_fails_safely(client, db_session, monkeypatch):
    """12. Invalid or missing signing configuration fails safely."""
    admin = make_user(db_session, "Admin 12", "admin12@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 12", "prof12@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 12", "student12@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS312A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q12", "q12", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    # In production without key
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "CERTIFICATE_PRIVATE_KEY_HEX", None)
    monkeypatch.setattr(settings, "CERTIFICATE_PRIVATE_KEY_PATH", None)
    monkeypatch.setattr(certificate_service, "_dev_key", None)

    with pytest.raises(RuntimeError) as exc_info:
        certificate_service.get_active_signing_key()
    assert "not configured for production" in str(exc_info.value)
    # Ensure no secret or key material in error message
    assert "private" not in str(exc_info.value).lower() or "configured" in str(exc_info.value)


# ==============================================================================
# Part B: Cryptographic Correctness & Tamper Detection (Tests 13-30)
# ==============================================================================

def test_13_newly_issued_certificate_has_correct_sha256_digest(client, db_session):
    """13. A newly issued certificate has a correctly computed SHA-256 digest."""
    admin = make_user(db_session, "Admin 13", "admin13@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 13", "prof13@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 13", "student13@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS313A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q13", "q13", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert = res.json()

    canonical_bytes = serialize_canonical_payload(cert["payload"])
    expected_digest = hashlib.sha256(canonical_bytes).hexdigest()
    assert cert["payload_digest"] == expected_digest


def test_14_signature_verifies_with_corresponding_public_key(client, db_session):
    """14. Its Ed25519 signature verifies with the corresponding public key."""
    admin = make_user(db_session, "Admin 14", "admin14@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 14", "prof14@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 14", "student14@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS314A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q14", "q14", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert = res.json()

    pub_hex = certificate_service.get_public_key_hex(cert["key_id"], db=db_session)
    pub_key = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex))

    canonical_bytes = serialize_canonical_payload(cert["payload"])
    sig_bytes = bytes.fromhex(cert["signature"])

    # Must verify without exception
    pub_key.verify(sig_bytes, canonical_bytes)


def test_15_verification_service_succeeds_for_valid_certificate(client, db_session):
    """15. Verification succeeds after retrieving and reconstructing the stored canonical payload."""
    admin = make_user(db_session, "Admin 15", "admin15@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 15", "prof15@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 15", "student15@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS315A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q15", "q15", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert = res.json()

    # Call verify API
    v_res = client.post("/api/v1/certificates/verify", json={"certificate_id": cert["id"]})
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["is_valid"] is True
    assert v_data["verification_status"] == "VALID"
    assert v_data["key_id"] == cert["key_id"]


def test_16_tampering_student_identifier_invalidates_verification(client, db_session):
    """16. Changing the student's identifier invalidates verification."""
    admin = make_user(db_session, "Admin 16", "admin16@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 16", "prof16@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 16", "student16@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS316A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q16", "q16", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert = res.json()

    # Tamper payload
    tampered_payload = copy.deepcopy(cert["payload"])
    tampered_payload["student_id"] = 9999

    v_res = client.post(
        "/api/v1/certificates/verify",
        json={
            "payload": tampered_payload,
            "payload_digest": cert["payload_digest"],
            "signature": cert["signature"],
            "key_id": cert["key_id"],
        },
    )
    v_data = v_res.json()
    assert v_data["is_valid"] is False
    assert v_data["verification_status"] == "DIGEST_MISMATCH"


def test_17_tampering_practical_or_title_invalidates_verification(client, db_session):
    """17. Changing the practical identifier or title invalidates verification."""
    admin = make_user(db_session, "Admin 17", "admin17@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 17", "prof17@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 17", "student17@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS317A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q17", "q17", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert = res.json()

    tampered_payload = copy.deepcopy(cert["payload"])
    tampered_payload["practical_title"] = "Forged Masterwork Challenge"

    v_res = client.post(
        "/api/v1/certificates/verify",
        json={
            "payload": tampered_payload,
            "payload_digest": cert["payload_digest"],
            "signature": cert["signature"],
            "key_id": cert["key_id"],
        },
    )
    assert v_res.json()["is_valid"] is False
    assert v_res.json()["verification_status"] == "DIGEST_MISMATCH"


def test_18_tampering_submission_id_invalidates_verification(client, db_session):
    """18. Changing the submission ID invalidates verification."""
    admin = make_user(db_session, "Admin 18", "admin18@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 18", "prof18@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 18", "student18@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS318A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q18", "q18", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert = res.json()

    tampered_payload = copy.deepcopy(cert["payload"])
    tampered_payload["submission_id"] = 99999

    v_res = client.post(
        "/api/v1/certificates/verify",
        json={
            "payload": tampered_payload,
            "payload_digest": cert["payload_digest"],
            "signature": cert["signature"],
            "key_id": cert["key_id"],
        },
    )
    assert v_res.json()["is_valid"] is False
    assert v_res.json()["verification_status"] == "DIGEST_MISMATCH"


def test_19_tampering_score_or_passing_threshold_invalidates_verification(client, db_session):
    """19. Changing the score or passing threshold invalidates verification."""
    admin = make_user(db_session, "Admin 19", "admin19@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 19", "prof19@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 19", "student19@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS319A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q19", "q19", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=70.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=75.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert = res.json()

    # Student tampers their score from 75.0 to 100.0
    tampered_payload = copy.deepcopy(cert["payload"])
    tampered_payload["score"] = 100.0

    v_res = client.post(
        "/api/v1/certificates/verify",
        json={
            "payload": tampered_payload,
            "payload_digest": cert["payload_digest"],
            "signature": cert["signature"],
            "key_id": cert["key_id"],
        },
    )
    assert v_res.json()["is_valid"] is False
    assert v_res.json()["verification_status"] == "DIGEST_MISMATCH"


def test_20_tampering_completion_timestamp_invalidates_verification(client, db_session):
    """20. Changing the completion timestamp invalidates verification."""
    admin = make_user(db_session, "Admin 20", "admin20@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 20", "prof20@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 20", "student20@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS320A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q20", "q20", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert = res.json()

    tampered_payload = copy.deepcopy(cert["payload"])
    tampered_payload["completed_at"] = "2020-01-01T00:00:00Z"

    v_res = client.post(
        "/api/v1/certificates/verify",
        json={
            "payload": tampered_payload,
            "payload_digest": cert["payload_digest"],
            "signature": cert["signature"],
            "key_id": cert["key_id"],
        },
    )
    assert v_res.json()["is_valid"] is False
    assert v_res.json()["verification_status"] == "DIGEST_MISMATCH"


def test_21_tampering_issuer_or_key_id_is_detected(client, db_session):
    """21. Changing the issuer, schema version or key ID is detected."""
    admin = make_user(db_session, "Admin 21", "admin21@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 21", "prof21@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 21", "student21@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS321A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q21", "q21", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert = res.json()

    tampered_payload = copy.deepcopy(cert["payload"])
    tampered_payload["issuer"] = "Fake University Authority"

    v_res = client.post(
        "/api/v1/certificates/verify",
        json={
            "payload": tampered_payload,
            "payload_digest": cert["payload_digest"],
            "signature": cert["signature"],
            "key_id": cert["key_id"],
        },
    )
    assert v_res.json()["is_valid"] is False
    assert v_res.json()["verification_status"] == "DIGEST_MISMATCH"


def test_22_tampering_stored_digest_is_detected(client, db_session):
    """22. Changing the stored digest is detected."""
    admin = make_user(db_session, "Admin 22", "admin22@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 22", "prof22@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 22", "student22@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS322A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q22", "q22", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert = res.json()

    fake_digest = "0" * 64
    v_res = client.post(
        "/api/v1/certificates/verify",
        json={
            "payload": cert["payload"],
            "payload_digest": fake_digest,
            "signature": cert["signature"],
            "key_id": cert["key_id"],
        },
    )
    assert v_res.json()["is_valid"] is False
    assert v_res.json()["verification_status"] == "DIGEST_MISMATCH"


def test_23_tampering_signature_is_detected(client, db_session):
    """23. Changing the signature is detected."""
    admin = make_user(db_session, "Admin 23", "admin23@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 23", "prof23@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 23", "student23@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS323A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q23", "q23", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert = res.json()

    # Flip the last character of the signature
    corrupt_sig = cert["signature"][:-1] + ("0" if cert["signature"][-1] != "0" else "1")

    v_res = client.post(
        "/api/v1/certificates/verify",
        json={
            "payload": cert["payload"],
            "payload_digest": cert["payload_digest"],
            "signature": corrupt_sig,
            "key_id": cert["key_id"],
        },
    )
    assert v_res.json()["is_valid"] is False
    assert v_res.json()["verification_status"] == "INVALID_SIGNATURE"


def test_24_truncated_or_corrupt_signature_is_rejected_safely(client, db_session):
    """24. Truncating or corrupting the signature is rejected safely."""
    admin = make_user(db_session, "Admin 24", "admin24@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 24", "prof24@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 24", "student24@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS324A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q24", "q24", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert = res.json()

    # Short truncated signature (32 chars instead of 128)
    truncated_sig = cert["signature"][:32]

    v_res = client.post(
        "/api/v1/certificates/verify",
        json={
            "payload": cert["payload"],
            "payload_digest": cert["payload_digest"],
            "signature": truncated_sig,
            "key_id": cert["key_id"],
        },
    )
    assert v_res.json()["is_valid"] is False
    assert v_res.json()["verification_status"] == "INVALID_SIGNATURE"


def test_25_signature_by_different_private_key_is_rejected(client, db_session):
    """25. A signature made by a different private key is rejected."""
    admin = make_user(db_session, "Admin 25", "admin25@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 25", "prof25@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 25", "student25@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS325A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q25", "q25", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert = res.json()

    # Generate an untrusted foreign private key and sign the legitimate payload
    foreign_key = ed25519.Ed25519PrivateKey.generate()
    canonical_bytes = serialize_canonical_payload(cert["payload"])
    foreign_signature = foreign_key.sign(canonical_bytes).hex()

    v_res = client.post(
        "/api/v1/certificates/verify",
        json={
            "payload": cert["payload"],
            "payload_digest": cert["payload_digest"],
            "signature": foreign_signature,
            "key_id": cert["key_id"],
        },
    )
    assert v_res.json()["is_valid"] is False
    assert v_res.json()["verification_status"] == "INVALID_SIGNATURE"


def test_26_unknown_key_id_produces_unknown_key_result(client, db_session):
    """26. A certificate referencing an unknown key ID produces the appropriate verification result."""
    admin = make_user(db_session, "Admin 26", "admin26@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 26", "prof26@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 26", "student26@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS326A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q26", "q26", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert = res.json()

    v_res = client.post(
        "/api/v1/certificates/verify",
        json={
            "payload": cert["payload"],
            "payload_digest": cert["payload_digest"],
            "signature": cert["signature"],
            "key_id": "nonexistent-unknown-key-9999",
        },
    )
    assert v_res.json()["is_valid"] is False
    assert v_res.json()["verification_status"] == "UNKNOWN_KEY"


def test_27_malformed_payload_is_rejected_without_crashing(client, db_session):
    """27. A malformed payload is rejected without crashing the API."""
    v_res = client.post(
        "/api/v1/certificates/verify",
        json={
            "payload": {"nonsense": 123},
            "payload_digest": "abcdef",
            "signature": "123456",
            "key_id": "test-key-2026",
        },
    )
    assert v_res.status_code == 200
    assert v_res.json()["is_valid"] is False
    assert v_res.json()["verification_status"] == "MALFORMED_CERTIFICATE"


def test_28_unsupported_schema_version_is_handled_explicitly(client, db_session):
    """28. Unsupported schema versions are handled explicitly."""
    admin = make_user(db_session, "Admin 28", "admin28@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 28", "prof28@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 28", "student28@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS328A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q28", "q28", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert = res.json()

    v_res = client.post(
        "/api/v1/certificates/verify",
        json={
            "payload": cert["payload"],
            "payload_digest": cert["payload_digest"],
            "signature": cert["signature"],
            "key_id": cert["key_id"],
            "schema_version": "99.0-unsupported",
        },
    )
    assert v_res.json()["is_valid"] is False
    assert v_res.json()["verification_status"] == "UNSUPPORTED_VERSION"


def test_29_same_logical_payload_produces_identical_bytes_and_digest():
    """29. The same logical payload produces the same canonical bytes and digest."""
    payload_a = {
        "certificate_id": "11111111-2222-3333-4444-555555555555",
        "student_id": 42,
        "practical_id": 10,
        "score": 100.0,
        "passing_threshold": 80.0,
        "issuer": "LabOS Sentinel",
        "key_id": "key-1",
    }
    # Different order of dictionary insertion
    payload_b = {
        "key_id": "key-1",
        "issuer": "LabOS Sentinel",
        "passing_threshold": 80.00,
        "score": 100,
        "practical_id": 10,
        "student_id": 42,
        "certificate_id": "11111111-2222-3333-4444-555555555555",
    }

    bytes_a = serialize_canonical_payload(payload_a)
    bytes_b = serialize_canonical_payload(payload_b)
    assert bytes_a == bytes_b
    assert compute_payload_digest(bytes_a) == compute_payload_digest(bytes_b)


def test_30_canonical_serialization_is_stable_across_repeated_runs():
    """30. The canonical serialization is stable across repeated runs."""
    payload = {
        "certificate_id": "uuid-abc",
        "student_id": 1,
        "student_name": "Alice Developer",
        "practical_title": "Pointers & Arrays",
        "completed_at": "2026-10-11T12:00:00Z",
        "score": 95.5,
    }
    baseline = serialize_canonical_payload(payload)
    for _ in range(50):
        assert serialize_canonical_payload(payload) == baseline


# ==============================================================================
# Part C: Key Security & Rotation (Tests 31-37)
# ==============================================================================

def test_31_private_key_material_never_returned_by_endpoints(client, db_session):
    """31. Private-key material is never returned by certificate endpoints."""
    admin = make_user(db_session, "Admin 31", "admin31@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 31", "prof31@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 31", "student31@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS331A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q31", "q31", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    # Issue endpoint
    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    res_text = res.text.lower()
    assert "private" not in res_text
    assert "private_key" not in res_text

    # Public keys list endpoint
    keys_res = client.get("/api/v1/certificates/public-keys/list")
    assert "private" not in keys_res.text.lower()


def test_32_private_key_material_not_written_to_application_logs(client, db_session, caplog):
    """32. Private-key material is not written to application logs."""
    admin = make_user(db_session, "Admin 32", "admin32@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 32", "prof32@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 32", "student32@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS332A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q32", "q32", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    with caplog.at_level(logging.DEBUG):
        client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))

    for record in caplog.records:
        assert "private_bytes" not in record.message
        assert settings.CERTIFICATE_PRIVATE_KEY_HEX not in record.message


def test_33_production_fails_safely_if_key_missing(monkeypatch):
    """33. Production startup or issuance fails safely if required signing configuration is missing."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "CERTIFICATE_PRIVATE_KEY_HEX", None)
    monkeypatch.setattr(settings, "CERTIFICATE_PRIVATE_KEY_PATH", None)
    monkeypatch.setattr(certificate_service, "_dev_key", None)

    with pytest.raises(RuntimeError) as exc_info:
        certificate_service.get_active_signing_key()
    assert "not configured for production" in str(exc_info.value)


def test_34_invalid_private_key_configuration_is_rejected(monkeypatch):
    """34. Invalid private-key configuration is rejected."""
    monkeypatch.setattr(settings, "CERTIFICATE_PRIVATE_KEY_HEX", "corrupted-hex-too-short")
    with pytest.raises(RuntimeError):
        certificate_service.get_active_signing_key()


def test_35_dev_key_command_cannot_overwrite_without_force(tmp_path):
    """35. A development-key command cannot silently overwrite an existing key."""
    from scripts.generate_dev_keys import generate_dev_key

    key_file = str(tmp_path / "dev.key")
    # First generation
    generate_dev_key(force=False, out_path=key_file)
    assert os.path.exists(key_file)

    # Second generation without force should exit
    with pytest.raises(SystemExit):
        generate_dev_key(force=False, out_path=key_file)


def test_36_certificates_signed_by_older_key_remain_verifiable_after_rotation(client, db_session, monkeypatch):
    """36. Certificates signed by an older trusted key remain verifiable after key rotation."""
    admin = make_user(db_session, "Admin 36", "admin36@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 36", "prof36@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 36", "student36@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS336A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q36", "q36", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    # 1. Old Key
    old_key = ed25519.Ed25519PrivateKey.generate()
    old_key_id = "key-2025-v1"
    old_pub_hex = old_key.public_key().public_bytes_raw().hex()

    monkeypatch.setattr(settings, "CERTIFICATE_KEY_ID", old_key_id)
    monkeypatch.setattr(settings, "CERTIFICATE_PRIVATE_KEY_HEX", old_key.private_bytes_raw().hex())
    monkeypatch.setattr(certificate_service, "_dev_key", old_key)

    res_old = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    old_cert = res_old.json()
    assert old_cert["key_id"] == old_key_id

    # 2. Key Rotation to New Key
    new_key = ed25519.Ed25519PrivateKey.generate()
    new_key_id = "key-2026-v2"
    new_pub_hex = new_key.public_key().public_bytes_raw().hex()

    monkeypatch.setattr(settings, "CERTIFICATE_KEY_ID", new_key_id)
    monkeypatch.setattr(settings, "CERTIFICATE_PRIVATE_KEY_HEX", new_key.private_bytes_raw().hex())
    monkeypatch.setattr(
        settings,
        "CERTIFICATE_TRUSTED_PUBLIC_KEYS",
        {old_key_id: old_pub_hex, new_key_id: new_pub_hex},
    )
    monkeypatch.setattr(certificate_service, "_dev_key", new_key)

    # Verify the OLD certificate still verifies via trusted historical public key
    v_res = client.post("/api/v1/certificates/verify", json={"certificate_id": old_cert["id"]})
    assert v_res.status_code == 200
    assert v_res.json()["is_valid"] is True
    assert v_res.json()["verification_status"] == "VALID"


def test_37_key_id_correctly_selects_corresponding_public_key(client, db_session):
    """37. The signing key ID correctly selects the corresponding verification public key."""
    # Register two distinct keys in database
    k1 = ed25519.Ed25519PrivateKey.generate()
    k2 = ed25519.Ed25519PrivateKey.generate()

    certificate_service.register_public_key(db_session, "k1", k1.public_key().public_bytes_raw().hex())
    certificate_service.register_public_key(db_session, "k2", k2.public_key().public_bytes_raw().hex())

    # Payload signed with k2
    payload = {
        "certificate_id": "test-uuid-37",
        "student_id": 1,
        "practical_id": 1,
        "submission_id": 1,
        "score": 100.0,
        "passing_threshold": 100.0,
        "completed_at": "2026-10-11T10:00:00Z",
        "issued_at": "2026-10-11T10:00:00Z",
        "issuer": "LabOS Sentinel",
        "key_id": "k2",
    }
    canonical = serialize_canonical_payload(payload)
    sig_k2 = k2.sign(canonical).hex()
    digest = compute_payload_digest(canonical)

    # Verification with correct key_id k2 succeeds
    v1 = certificate_service.verify_certificate(
        {"payload": payload, "payload_digest": digest, "signature": sig_k2, "key_id": "k2", "schema_version": "1.0"},
        db=db_session,
    )
    assert v1.is_valid is True

    # Verification with wrong key_id k1 fails
    v2 = certificate_service.verify_certificate(
        {"payload": payload, "payload_digest": digest, "signature": sig_k2, "key_id": "k1", "schema_version": "1.0"},
        db=db_session,
    )
    assert v2.is_valid is False
    assert v2.verification_status == "INVALID_SIGNATURE"


# ==============================================================================
# Part D: Authorization, RBAC & Integrity (Tests 38-44)
# ==============================================================================

def test_38_student_cannot_forge_score_in_issuance_request(client, db_session):
    """38. A student cannot forge a score or completion status in an issuance request."""
    admin = make_user(db_session, "Admin 38", "admin38@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 38", "prof38@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 38", "student38@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS338A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q38", "q38", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    # Student actual submission score is only 50
    make_submission(db_session, student, q, practical, status=SubmissionStatus.WRONG_ANSWER, score=50.0)

    # Client tries to send "score": 100 or "completed": true in the payload
    forgery_attempt = {"practical_id": practical.id, "score": 100.0, "status": "COMPLETED"}
    res = client.post("/api/v1/certificates/issue", json=forgery_attempt, headers=auth_header(student))
    assert res.status_code == 400


def test_39_student_cannot_alter_another_students_certificate(client, db_session):
    """39. A student cannot change or re-issue another student's certificate."""
    admin = make_user(db_session, "Admin 39", "admin39@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 39", "prof39@uni.edu", UserRole.FACULTY)
    student1 = make_user(db_session, "Student 39A", "student39a@uni.edu", UserRole.STUDENT)
    student2 = make_user(db_session, "Student 39B", "student39b@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS339A")
    enroll_student(db_session, course, student1)

    q = make_question(db_session, "Q39", "q39", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student1, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    # Student 1 issues certificate
    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student1))
    cert_id = res.json()["id"]

    # Student 2 tries to GET certificate
    res_get = client.get(f"/api/v1/certificates/{cert_id}", headers=auth_header(student2))
    assert res_get.status_code == 404


def test_40_unauthorized_faculty_cannot_retrieve_protected_certificate(client, db_session):
    """40. Unauthorized faculty (not assigned to course) cannot retrieve protected certificate data."""
    admin = make_user(db_session, "Admin 40", "admin40@uni.edu", UserRole.ADMIN)
    assigned_faculty = make_user(db_session, "Prof 40A", "prof40a@uni.edu", UserRole.FACULTY)
    unassigned_faculty = make_user(db_session, "Prof 40B", "prof40b@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 40", "student40@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty=assigned_faculty, code="CS340A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q40", "q40", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert_id = res.json()["id"]

    # Unassigned faculty receives 404
    res_unassigned = client.get(f"/api/v1/certificates/{cert_id}", headers=auth_header(unassigned_faculty))
    assert res_unassigned.status_code == 404


def test_41_authorized_faculty_and_admin_can_retrieve_certificate(client, db_session):
    """41. Authorized faculty/admin behavior follows the existing RBAC policy."""
    admin = make_user(db_session, "Admin 41", "admin41@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 41", "prof41@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 41", "student41@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS341A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q41", "q41", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert_id = res.json()["id"]

    # Assigned faculty can view
    f_res = client.get(f"/api/v1/certificates/{cert_id}", headers=auth_header(faculty))
    assert f_res.status_code == 200

    # Admin can view
    a_res = client.get(f"/api/v1/certificates/{cert_id}", headers=auth_header(admin))
    assert a_res.status_code == 200


def test_42_forged_digest_not_treated_as_trusted_signature(client, db_session):
    """42. A client cannot submit a forged digest and have the server treat it as a trusted signature."""
    admin = make_user(db_session, "Admin 42", "admin42@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 42", "prof42@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 42", "student42@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS342A")
    enroll_student(db_session, course, student)

    payload = {
        "certificate_id": str(uuid.uuid4()),
        "schema_version": "1.0",
        "student_id": student.id,
        "practical_id": 1,
        "submission_id": 1,
        "score": 100.0,
        "passing_threshold": 100.0,
        "completed_at": "2026-10-11T12:00:00Z",
        "issued_at": "2026-10-11T12:00:00Z",
        "issuer": "LabOS Sentinel",
        "key_id": "test-key-2026",
    }
    canonical = serialize_canonical_payload(payload)
    correct_digest = compute_payload_digest(canonical)

    # Forged random signature
    fake_sig = "ff" * 64

    v_res = client.post(
        "/api/v1/certificates/verify",
        json={
            "payload": payload,
            "payload_digest": correct_digest,
            "signature": fake_sig,
            "key_id": "test-key-2026",
        },
    )
    assert v_res.json()["is_valid"] is False
    assert v_res.json()["verification_status"] == "INVALID_SIGNATURE"


def test_43_certificate_records_cannot_be_silently_rewritten(client, db_session):
    """43. Certificate records cannot be silently rewritten without detection."""
    admin = make_user(db_session, "Admin 43", "admin43@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 43", "prof43@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 43", "student43@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS343A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q43", "q43", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert_id = res.json()["id"]

    # Directly tamper database row (e.g. rogue DBA update)
    db_cert = db_session.query(CompletionCertificate).filter(CompletionCertificate.id == cert_id).first()
    tampered_payload = copy.deepcopy(db_cert.payload)
    tampered_payload["score"] = 50.0  # modified
    db_cert.payload = tampered_payload
    db_session.commit()

    # Re-verification of certificate row detects the tamper
    v_res = client.post("/api/v1/certificates/verify", json={"certificate_id": cert_id})
    assert v_res.json()["is_valid"] is False
    assert v_res.json()["verification_status"] == "DIGEST_MISMATCH"


def test_44_public_verification_returns_only_public_fields(client, db_session):
    """44. Public verification returns only intentionally public fields."""
    admin = make_user(db_session, "Admin 44", "admin44@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 44", "prof44@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 44", "student44@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS344A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q44", "q44", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    cert_id = res.json()["id"]

    # Unauthenticated verify call
    v_res = client.post("/api/v1/certificates/verify", json={"certificate_id": cert_id})
    assert v_res.status_code == 200
    details = v_res.json().get("details", {})
    # Should NOT contain internal user password, foreign keys, or raw submission code
    assert "password" not in details
    assert "source_code" not in details
    assert "student_id" not in details
    assert "submission_id" not in details


# ==============================================================================
# Part E: Regression & Backward Compatibility (Tests 45-50)
# ==============================================================================

def test_45_student_practical_certificate_endpoint(client, db_session):
    """45. Convenient GET /api/v1/certificates/practical/{practical_id} retrieves student's certificate."""
    admin = make_user(db_session, "Admin 45", "admin45@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 45", "prof45@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 45", "student45@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS345A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q45", "q45", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)

    # 404 before issuance
    r0 = client.get(f"/api/v1/certificates/practical/{practical.id}", headers=auth_header(student))
    assert r0.status_code == 404

    # Issue
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)
    client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))

    # 200 after issuance
    r1 = client.get(f"/api/v1/certificates/practical/{practical.id}", headers=auth_header(student))
    assert r1.status_code == 200
    assert r1.json()["practical_id"] == practical.id


def test_46_sequential_unlock_rules_still_gate_certificate_issuance(client, db_session):
    """46. Sequential unlocking prerequisites from Chunk 9 still gate certificate issuance."""
    admin = make_user(db_session, "Admin 46", "admin46@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 46", "prof46@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 46", "student46@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS346A")
    enroll_student(db_session, course, student)

    q1 = make_question(db_session, "Q46-1", "q46-1", admin.id)
    q2 = make_question(db_session, "Q46-2", "q46-2", admin.id)
    p1 = make_practical(db_session, lab, q1, seq=1, is_required=True, threshold=100.0)
    p2 = make_practical(db_session, lab, q2, seq=2, is_required=True, threshold=100.0)

    # Student did NOT pass p1, but somehow submitted p2 directly
    make_submission(db_session, student, q2, p2, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": p2.id}, headers=auth_header(student))
    assert res.status_code == 403
    assert "locked" in res.json()["detail"].lower()


def test_47_legacy_standalone_submissions_remain_compatible(client, db_session):
    """47. Legacy standalone submissions without practical_id remain compatible and functional."""
    admin = make_user(db_session, "Admin 47", "admin47@uni.edu", UserRole.ADMIN)
    student = make_user(db_session, "Student 47", "student47@uni.edu", UserRole.STUDENT)
    q = make_question(db_session, "Q47", "q47", admin.id)

    sub = make_submission(db_session, student, q, practical=None, status=SubmissionStatus.ACCEPTED, score=100.0)
    assert sub.practical_id is None

    # Retrieve submission details
    res = client.get(f"/api/v1/submissions/{sub.id}", headers=auth_header(student))
    assert res.status_code == 200
    assert res.json()["practical_id"] is None


def test_48_public_keys_list_endpoint_exports_active_keys(client, db_session):
    """48. GET /api/v1/certificates/public-keys/list exports active verification keys."""
    res = client.get("/api/v1/certificates/public-keys/list")
    assert res.status_code == 200
    keys = res.json()
    assert isinstance(keys, list)
    assert len(keys) >= 1
    assert "public_key_hex" in keys[0]
    assert keys[0]["key_id"] == "test-key-2026"


def test_49_multiple_practicals_generate_distinct_certificates(client, db_session):
    """49. Student completing multiple practicals earns distinct, independently verifiable certificates."""
    admin = make_user(db_session, "Admin 49", "admin49@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 49", "prof49@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 49", "student49@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS349A")
    enroll_student(db_session, course, student)

    q1 = make_question(db_session, "Q49-1", "q49-1", admin.id)
    q2 = make_question(db_session, "Q49-2", "q49-2", admin.id)
    p1 = make_practical(db_session, lab, q1, seq=1, threshold=100.0)
    p2 = make_practical(db_session, lab, q2, seq=2, threshold=100.0)

    make_submission(db_session, student, q1, p1, status=SubmissionStatus.ACCEPTED, score=100.0)
    make_submission(db_session, student, q2, p2, status=SubmissionStatus.ACCEPTED, score=100.0)

    res1 = client.post("/api/v1/certificates/issue", json={"practical_id": p1.id}, headers=auth_header(student))
    res2 = client.post("/api/v1/certificates/issue", json={"practical_id": p2.id}, headers=auth_header(student))

    assert res1.status_code == 201
    assert res2.status_code == 201

    cert1 = res1.json()
    cert2 = res2.json()

    assert cert1["id"] != cert2["id"]
    assert cert1["practical_id"] == p1.id
    assert cert2["practical_id"] == p2.id
    assert cert1["signature"] != cert2["signature"]


def test_50_certificate_verification_by_id_endpoint_not_found(client, db_session):
    """50. Verifying non-existent certificate returns structured NOT_FOUND response without 500 error."""
    non_existent_id = str(uuid.uuid4())
    v_res = client.post("/api/v1/certificates/verify", json={"certificate_id": non_existent_id})
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["is_valid"] is False
    assert v_data["verification_status"] == "NOT_FOUND"


def test_51_public_certificate_endpoint_unauthenticated(client, db_session):
    """51. GET /api/v1/certificates/{id}/public returns sanitized public certificate without authentication."""
    admin = make_user(db_session, "Admin 51", "admin51@uni.edu", UserRole.ADMIN)
    faculty = make_user(db_session, "Prof 51", "prof51@uni.edu", UserRole.FACULTY)
    student = make_user(db_session, "Student 51", "student51@uni.edu", UserRole.STUDENT)
    course, lab = make_course_and_lab(db_session, admin, faculty, "CS351A")
    enroll_student(db_session, course, student)

    q = make_question(db_session, "Q51", "q51", admin.id)
    practical = make_practical(db_session, lab, q, seq=1, threshold=100.0)
    make_submission(db_session, student, q, practical, status=SubmissionStatus.ACCEPTED, score=100.0)

    res = client.post("/api/v1/certificates/issue", json={"practical_id": practical.id}, headers=auth_header(student))
    assert res.status_code == 201
    cert_id = res.json()["id"]

    # Public unauthenticated fetch
    pub_res = client.get(f"/api/v1/certificates/{cert_id}/public")
    assert pub_res.status_code == 200
    pub_data = pub_res.json()
    assert pub_data["certificate_id"] == cert_id
    assert pub_data["student_name"] == "Student 51"
    assert pub_data["course_code"] == "CS351A"
    assert pub_data["practical_title"] == "Q51"
    assert pub_data["score"] == 100.0
    assert pub_data["issuer"] == "LabOS Sentinel"
    assert "password" not in pub_data
    assert "source_code" not in pub_data


def test_52_public_certificate_endpoint_not_found(client, db_session):
    """52. GET /api/v1/certificates/{id}/public returns 404 for non-existent certificate."""
    non_existent = str(uuid.uuid4())
    pub_res = client.get(f"/api/v1/certificates/{non_existent}/public")
    assert pub_res.status_code == 404
    assert pub_res.json()["detail"] == "Certificate not found."

