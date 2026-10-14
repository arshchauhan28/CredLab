"""
API Endpoints for Cryptographic Completion Certificates (Chunk 10).
Provides endpoints for:
- Issuing completion certificates for eligible practicals.
- Retrieving full certificate records for authorized users.
- Querying certificate by practical ID for the authenticated student.
- Cryptographically verifying certificates by ID or raw payload.
- Listing trusted public keys for external verification.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    bearer_scheme,
    get_current_user,
    is_faculty_assigned_to_course,
    get_current_faculty_or_admin,
)
from app.core.database import get_db
from app.models.certificate import CertificateSigningKey, CompletionCertificate, CertificateApprovalRequest, SubjectCertificateRequest
from app.models.badge import Badge
from app.models.university import Course, CourseEnrollment
from app.models.user import User, UserRole
from app.models.university import Lab, LabPractical, FacultyCourseAssignment
from app.models.submission import Submission, SubmissionStatus
from app.schemas.certificate import (
    CertificateIssueRequest,
    CertificatePublicResponse,
    CertificateResponse,
    CertificateVerifyRequest,
    CertificateVerifyResponse,
    PublicKeyInfo,
)
from app.services.certificate import certificate_service
from app.services.badge_service import award_badge_if_eligible

router = APIRouter()


def _build_certificate_response(cert: CompletionCertificate) -> CertificateResponse:
    """Builds a complete, typed CertificateResponse from an ORM model."""
    student_name = cert.student.name if cert.student else cert.payload.get("student_name", "Student")
    course_id = cert.payload.get("course_id", 0)
    course_code = cert.payload.get("course_code", "")
    lab_id = cert.payload.get("lab_id", 0)
    lab_title = cert.payload.get("lab_title", "")
    practical_title = cert.payload.get("practical_title", "")
    score = cert.payload.get("score", 0.0)
    passing_threshold = cert.payload.get("passing_threshold", 100.0)

    if cert.practical:
        if cert.practical.lab:
            lab_id = cert.practical.lab.id
            lab_title = cert.practical.lab.title
            if cert.practical.lab.course:
                course_id = cert.practical.lab.course.id
                course_code = cert.practical.lab.course.code or cert.practical.lab.course.name
        practical_title = (
            cert.practical.title
            if cert.practical.title
            else (cert.practical.question.title if cert.practical.question else practical_title)
        )
        passing_threshold = cert.practical.passing_threshold

    if cert.submission:
        score = cert.submission.score

    return CertificateResponse(
        id=cert.id,
        student_id=cert.student_id,
        student_name=student_name,
        course_id=course_id,
        course_code=course_code,
        lab_id=lab_id,
        lab_title=lab_title,
        practical_id=cert.practical_id,
        practical_title=practical_title,
        submission_id=cert.submission_id,
        score=score,
        passing_threshold=passing_threshold,
        schema_version=cert.schema_version,
        issuer=cert.issuer,
        algorithm=cert.algorithm,
        key_id=cert.key_id,
        payload=cert.payload,
        payload_digest=cert.payload_digest,
        signature=cert.signature,
        status=cert.status,
        certificate_type=getattr(cert, "certificate_type", "PRACTICAL") or "PRACTICAL",
        completed_at=cert.completed_at,
        issued_at=cert.issued_at,
        created_at=cert.created_at,
    )


@router.post(
    "/issue",
    response_model=CertificateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a completion certificate for a completed lab practical",
)
def issue_certificate(
    payload: CertificateIssueRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Issues a tamper-evident, Ed25519 digitally signed completion certificate.
    Requirements:
    - User must be enrolled in the course.
    - All preceding required practicals must be completed (Chunk 9).
    - User must have a verified passing submission for this practical.
    - Idempotent: Returns the existing active certificate if already issued.
    """
    cert = certificate_service.issue_certificate_for_practical(
        db=db,
        student=current_user,
        practical_id=payload.practical_id,
    )
    return _build_certificate_response(cert)


@router.get(
    "/practical/{practical_id}",
    response_model=CertificateResponse,
    summary="Get authenticated student's certificate for a specific practical",
)
def get_student_practical_certificate(
    practical_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves the active certificate for the given practical issued to the current user.
    """
    cert = (
        db.query(CompletionCertificate)
        .filter(
            CompletionCertificate.practical_id == practical_id,
            CompletionCertificate.student_id == current_user.id,
            CompletionCertificate.status == "ACTIVE",
        )
        .first()
    )
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No completion certificate found for this practical.",
        )
    return _build_certificate_response(cert)


@router.get("/mine", summary="List the authenticated student's certificates and approval requests")
def list_my_certificates(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Student access required.")
    certificates = db.query(CompletionCertificate).filter(CompletionCertificate.student_id == current_user.id).order_by(CompletionCertificate.issued_at.desc()).all()
    requests = db.query(CertificateApprovalRequest).filter(CertificateApprovalRequest.student_id == current_user.id).order_by(CertificateApprovalRequest.requested_at.desc()).all()
    return {
        "certificates": [{"id": c.id, "status": c.status, "lab_title": (c.payload or {}).get("lab_title", "Completed lab"), "practical_title": (c.payload or {}).get("practical_title", "Practical"), "issued_at": c.issued_at, "payload_digest": c.payload_digest} for c in certificates],
        "requests": [{"id": r.id, "lab_id": r.lab_id, "lab_title": r.lab.title if r.lab else "Lab", "status": r.status, "review_note": r.review_note, "requested_at": r.requested_at, "reviewed_at": r.reviewed_at} for r in requests],
    }


@router.get("/approvals", summary="List certificate approval requests for assigned courses")
@router.get("/requests", summary="List certificate approval requests for assigned courses (Compatibility alias)", include_in_schema=False)
def list_certificate_approvals(current_user: User = Depends(get_current_faculty_or_admin), db: Session = Depends(get_db)):
    query = db.query(CertificateApprovalRequest).join(CertificateApprovalRequest.lab).join(CertificateApprovalRequest.student)
    if current_user.role == UserRole.FACULTY:
        assigned_course_ids = db.query(FacultyCourseAssignment.course_id).filter(FacultyCourseAssignment.faculty_id == current_user.id)
        query = query.filter(Lab.course_id.in_(assigned_course_ids))
    requests = query.order_by(CertificateApprovalRequest.requested_at.desc()).all()
    return {"items": [{"id": r.id, "student_id": r.student_id, "student_name": r.student.name if r.student else "Student", "student_email": r.student.email if r.student else "", "lab_id": r.lab_id, "lab_title": r.lab.title if r.lab else "Lab", "course_id": r.lab.course_id if r.lab else None, "practical_id": r.practical_id, "submission_id": r.submission_id, "status": r.status, "review_note": r.review_note, "requested_at": r.requested_at} for r in requests]}


@router.post("/approvals/{request_id}", summary="Approve or reject a lab certificate request")
@router.post("/requests/{request_id}/review", summary="Approve or reject a lab certificate request (Compatibility alias)", include_in_schema=False)
def review_certificate_approval(request_id: int, payload: dict, current_user: User = Depends(get_current_faculty_or_admin), db: Session = Depends(get_db)):
    action = str(payload.get("action", "")).strip().upper()
    note = str(payload.get("note", "") or payload.get("review_note", "")).strip() or None
    if action not in {"APPROVE", "REJECT"}:
        raise HTTPException(status_code=422, detail="action must be APPROVE or REJECT.")
    request_record = db.query(CertificateApprovalRequest).filter(CertificateApprovalRequest.id == request_id).first()
    if not request_record:
        raise HTTPException(status_code=404, detail="Certificate approval request not found.")
    lab = db.query(Lab).filter(Lab.id == request_record.lab_id).first()
    if current_user.role == UserRole.FACULTY and (not lab or not is_faculty_assigned_to_course(lab.course_id, current_user.id, db)):
        raise HTTPException(status_code=403, detail="You are not assigned to this lab's subject.")
    if request_record.status != "PENDING":
        raise HTTPException(status_code=409, detail=f"This request has already been {request_record.status.lower()}.")
    request_record.reviewed_by = current_user.id
    request_record.review_note = note
    request_record.reviewed_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    if action == "REJECT":
        request_record.status = "REJECTED"
        db.commit()
        return {"status": request_record.status, "message": "Certificate request rejected."}
    student = db.query(User).filter(User.id == request_record.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student account not found.")
    try:
        certificate_service.issue_certificate_for_practical(db=db, student=student, practical_id=request_record.practical_id)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Certificate could not be issued. Check certificate signing-key configuration.") from None
    request_record.status = "APPROVED"
    db.commit()
    return {"status": request_record.status, "message": "Certificate approved and issued."}


@router.post("/subject-requests", summary="Student requests a subject-level completion certificate")
def request_subject_certificate(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submits a request for a subject completion certificate once all required practicals are completed.
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can request subject certificates.")

    course_id = payload.get("course_id")
    if not course_id:
        raise HTTPException(status_code=400, detail="course_id is required.")

    course = db.query(Course).filter(Course.id == course_id, Course.is_active.is_(True)).first()
    if not course:
        raise HTTPException(status_code=404, detail="Subject not found or inactive.")

    # Verify enrollment
    enrollment = db.query(CourseEnrollment).filter(
        CourseEnrollment.course_id == course.id,
        CourseEnrollment.student_id == current_user.id,
        CourseEnrollment.status == "ENROLLED",
    ).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="You are not enrolled in this subject.")

    # Check for existing active certificate
    existing_cert = db.query(CompletionCertificate).filter(
        CompletionCertificate.student_id == current_user.id,
        CompletionCertificate.course_id == course.id,
        CompletionCertificate.certificate_type == "SUBJECT",
        CompletionCertificate.status == "ACTIVE",
    ).first()
    if existing_cert:
        raise HTTPException(status_code=409, detail="A certificate for this subject has already been issued.")

    # Check for existing pending request
    existing_req = db.query(SubjectCertificateRequest).filter(
        SubjectCertificateRequest.student_id == current_user.id,
        SubjectCertificateRequest.course_id == course.id,
    ).first()
    if existing_req and existing_req.status == "PENDING":
        raise HTTPException(status_code=409, detail="A certificate request for this subject is already pending approval.")

    # Verify that all required practicals are passed
    lab_ids = [l.id for l in course.labs]
    if not lab_ids:
        raise HTTPException(status_code=400, detail="This subject currently has no laboratories.")

    required_practicals = db.query(LabPractical).filter(
        LabPractical.lab_id.in_(lab_ids),
        LabPractical.is_required.is_(True),
    ).all()
    if not required_practicals:
        raise HTTPException(status_code=400, detail="This subject currently has no required practicals.")

    for req in required_practicals:
        passed = db.query(Submission).filter(
            Submission.user_id == current_user.id,
            Submission.practical_id == req.id,
            Submission.status == SubmissionStatus.ACCEPTED,
            Submission.score >= req.passing_threshold,
        ).first()
        if not passed:
            prac_name = getattr(req, "effective_title", None) or getattr(req, "title", None) or (req.question.title if getattr(req, "question", None) else str(req.id))
            raise HTTPException(
                status_code=400,
                detail=f"Ineligible: You must pass required practical '{prac_name}' before requesting a certificate.",
            )

    from datetime import datetime, timezone
    if existing_req:
        # Re-request after rejection
        existing_req.status = "PENDING"
        existing_req.review_note = None
        existing_req.requested_at = datetime.now(timezone.utc)
        existing_req.reviewed_at = None
        existing_req.reviewed_by = None
        db.commit()
        db.refresh(existing_req)
        return {"id": existing_req.id, "status": existing_req.status, "message": "Subject certificate request submitted."}
    else:
        new_req = SubjectCertificateRequest(
            student_id=current_user.id,
            course_id=course.id,
            status="PENDING",
        )
        db.add(new_req)
        db.commit()
        db.refresh(new_req)
        return {"id": new_req.id, "status": new_req.status, "message": "Subject certificate request submitted."}


@router.get("/subject-approvals", summary="List subject certificate requests for assigned courses")
def list_subject_certificate_approvals(
    current_user: User = Depends(get_current_faculty_or_admin),
    db: Session = Depends(get_db),
):
    query = db.query(SubjectCertificateRequest).join(SubjectCertificateRequest.course).join(SubjectCertificateRequest.student)
    if current_user.role == UserRole.FACULTY:
        assigned_course_ids = db.query(FacultyCourseAssignment.course_id).filter(FacultyCourseAssignment.faculty_id == current_user.id)
        query = query.filter(SubjectCertificateRequest.course_id.in_(assigned_course_ids))

    requests = query.order_by(SubjectCertificateRequest.requested_at.desc()).all()
    items = []
    for r in requests:
        # Calculate practical stats for this student and course
        course = r.course
        lab_ids = [l.id for l in course.labs] if course else []
        req_count = db.query(LabPractical).filter(LabPractical.lab_id.in_(lab_ids), LabPractical.is_required.is_(True)).count() if lab_ids else 0
        items.append({
            "id": r.id,
            "student_id": r.student_id,
            "student_name": r.student.name if r.student else "Student",
            "student_email": r.student.email if r.student else "",
            "enrollment_number": r.student.enrollment_number if r.student else "",
            "course_id": r.course_id,
            "course_name": r.course.name if r.course else "Subject",
            "course_code": r.course.code if r.course else "",
            "total_required": req_count,
            "status": r.status,
            "review_note": r.review_note,
            "requested_at": r.requested_at,
            "reviewed_at": r.reviewed_at,
        })
    return {"items": items}


@router.post("/subject-approvals/{request_id}", summary="Approve or reject a subject certificate request")
def review_subject_certificate_approval(
    request_id: int,
    payload: dict,
    current_user: User = Depends(get_current_faculty_or_admin),
    db: Session = Depends(get_db),
):
    action = str(payload.get("action", "")).strip().upper()
    note = str(payload.get("note", "")).strip() or None
    if action not in {"APPROVE", "REJECT"}:
        raise HTTPException(status_code=422, detail="action must be APPROVE or REJECT.")

    req = db.query(SubjectCertificateRequest).filter(SubjectCertificateRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Subject certificate request not found.")

    if current_user.role == UserRole.FACULTY and not is_faculty_assigned_to_course(req.course_id, current_user.id, db):
        raise HTTPException(status_code=403, detail="You are not authorized to review certificates for this subject.")

    if req.status != "PENDING":
        raise HTTPException(status_code=409, detail=f"This request has already been {req.status.lower()}.")

    from datetime import datetime, timezone
    req.reviewed_by = current_user.id
    req.review_note = note
    req.reviewed_at = datetime.now(timezone.utc)

    if action == "REJECT":
        if not note:
            raise HTTPException(status_code=400, detail="A rejection reason is required.")
        req.status = "REJECTED"
        db.commit()
        return {"status": req.status, "message": "Subject certificate request rejected."}

    # APPROVE: revalidate eligibility and issue
    student = db.query(User).filter(User.id == req.student_id).first()
    course = db.query(Course).filter(Course.id == req.course_id).first()
    if not student or not course:
        raise HTTPException(status_code=404, detail="Student or Course not found.")

    try:
        cert = certificate_service.issue_subject_certificate(db=db, student=student, course=course)
        req.status = "APPROVED"
        db.commit()
        return {"status": req.status, "certificate_id": cert.id, "message": "Subject completion certificate approved and issued."}
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Certificate issuance failed: {exc}")


@router.get("/student-progress", summary="Get authenticated student course progress, badges, and certificates")
def get_student_academic_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students have academic progress records.")

    # 1. Enrolled courses
    enrollments = db.query(CourseEnrollment).join(CourseEnrollment.course).filter(
        CourseEnrollment.student_id == current_user.id,
        CourseEnrollment.status == "ENROLLED",
        Course.is_active.is_(True),
    ).all()

    progress_list = []
    for enr in enrollments:
        c = enr.course
        lab_ids = [l.id for l in c.labs]
        practicals = db.query(LabPractical).filter(
            LabPractical.lab_id.in_(lab_ids),
        ).all() if lab_ids else []

        required_practicals = [p for p in practicals if p.is_required]
        total_required = len(required_practicals)

        # Count completed practicals
        completed_count = 0
        req_ids = [p.id for p in required_practicals]
        if req_ids:
            for p in required_practicals:
                passed = db.query(Submission.id).filter(
                    Submission.user_id == current_user.id,
                    Submission.practical_id == p.id,
                    Submission.status == SubmissionStatus.ACCEPTED,
                    Submission.score >= p.passing_threshold,
                ).first()
                if passed:
                    completed_count += 1

        # Ensure badges are awarded for any passing practicals
        for p in practicals:
            passing_sub = (
                db.query(Submission)
                .filter(
                    Submission.user_id == current_user.id,
                    Submission.practical_id == p.id,
                    Submission.status == SubmissionStatus.ACCEPTED,
                    Submission.score >= p.passing_threshold,
                )
                .order_by(Submission.score.desc(), Submission.id.desc())
                .first()
            )
            if passing_sub:
                award_badge_if_eligible(db, current_user.id, p, passing_sub)

        # Badges earned for this course
        practical_ids = [p.id for p in practicals]
        badges_earned = db.query(Badge).filter(
            Badge.user_id == current_user.id,
            Badge.practical_id.in_(practical_ids),
        ).count() if practical_ids else 0

        # Certificate status
        subject_cert = db.query(CompletionCertificate).filter(
            CompletionCertificate.student_id == current_user.id,
            CompletionCertificate.course_id == c.id,
            CompletionCertificate.certificate_type == "SUBJECT",
            CompletionCertificate.status == "ACTIVE",
        ).first()

        cert_req = db.query(SubjectCertificateRequest).filter(
            SubjectCertificateRequest.student_id == current_user.id,
            SubjectCertificateRequest.course_id == c.id,
        ).first()

        if subject_cert:
            cert_status = "ISSUED"
            cert_id = subject_cert.id
        elif cert_req and cert_req.status == "PENDING":
            cert_status = "PENDING_APPROVAL"
            cert_id = None
        elif cert_req and cert_req.status == "REJECTED":
            cert_status = "REJECTED"
            cert_id = None
        elif total_required > 0 and completed_count >= total_required:
            cert_status = "ELIGIBLE"
            cert_id = None
        else:
            cert_status = "NOT_ELIGIBLE"
            cert_id = None

        pct = round((completed_count / total_required * 100), 1) if total_required > 0 else 0.0

        progress_list.append({
            "course_id": c.id,
            "course_name": c.name,
            "course_code": c.code or "",
            "total_required": total_required,
            "completed_required": completed_count,
            "remaining_required": max(0, total_required - completed_count),
            "completion_percentage": pct,
            "badges_earned": badges_earned,
            "certificate_status": cert_status,
            "certificate_id": cert_id,
            "rejection_note": cert_req.review_note if cert_req and cert_req.status == "REJECTED" else None,
        })

    # Also query all badges earned by the student
    all_badges = db.query(Badge).filter(Badge.user_id == current_user.id).order_by(Badge.earned_at.desc()).all()
    badges_data = [
        {
            "id": b.id,
            "name": b.name,
            "description": b.description,
            "icon": b.icon,
            "earned_at": b.earned_at,
            "practical_id": b.practical_id,
            "course_id": b.course_id,
            "meta": b.meta,
        }
        for b in all_badges
    ]

    return {
        "subjects": progress_list,
        "badges": badges_data,
    }

@router.get(
    "/{certificate_id}",
    response_model=CertificateResponse,
    summary="Retrieve certificate by certificate UUID",
)
def get_certificate_by_id(
    certificate_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves a certificate by UUID.
    Access control:
    - The owning student can view.
    - Faculty assigned to the course can view.
    - Administrators can view.
    - Unauthorized users receive 404 to avoid leaking record existence.
    """
    cert = (
        db.query(CompletionCertificate)
        .filter(CompletionCertificate.id == certificate_id)
        .first()
    )
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found.",
        )

    # Authorization verification
    if current_user.role == UserRole.ADMIN:
        return _build_certificate_response(cert)

    if current_user.id == cert.student_id:
        return _build_certificate_response(cert)

    if current_user.role == UserRole.FACULTY:
        course_id = cert.payload.get("course_id")
        if course_id and is_faculty_assigned_to_course(course_id, current_user.id, db):
            return _build_certificate_response(cert)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Certificate not found.",
    )


def _build_public_certificate_response(cert: CompletionCertificate) -> CertificatePublicResponse:
    student_name = cert.student.name if cert.student else cert.payload.get("student_name", "Student")
    course_code = cert.payload.get("course_code", "")
    lab_title = cert.payload.get("lab_title", "")
    practical_title = cert.payload.get("practical_title", "")
    score = cert.payload.get("score", 0.0)
    passing_threshold = cert.payload.get("passing_threshold", 100.0)

    if cert.practical:
        if cert.practical.lab:
            lab_title = cert.practical.lab.title
            if cert.practical.lab.course:
                course_code = cert.practical.lab.course.code or cert.practical.lab.course.name
        practical_title = (
            cert.practical.title
            if cert.practical.title
            else (cert.practical.question.title if cert.practical.question else practical_title)
        )
        passing_threshold = cert.practical.passing_threshold

    if cert.submission:
        score = cert.submission.score

    return CertificatePublicResponse(
        certificate_id=cert.id,
        student_name=student_name,
        course_code=course_code,
        lab_title=lab_title,
        practical_title=practical_title,
        score=score,
        passing_threshold=passing_threshold,
        completed_at=cert.completed_at.isoformat() if hasattr(cert.completed_at, "isoformat") else str(cert.completed_at),
        issued_at=cert.issued_at.isoformat() if hasattr(cert.issued_at, "isoformat") else str(cert.issued_at),
        issuer=cert.issuer,
        algorithm=cert.algorithm,
        key_id=cert.key_id,
        payload_digest=cert.payload_digest,
        signature=cert.signature,
        status=cert.status,
    )


@router.get(
    "/{certificate_id}/public",
    response_model=CertificatePublicResponse,
    summary="Retrieve sanitized public certificate details by UUID (Public / Unauthenticated)",
)
def get_public_certificate(
    certificate_id: str,
    db: Session = Depends(get_db),
):
    """
    Publicly exposes non-sensitive certificate details for verification displays.
    Requires no authentication.
    """
    cert = (
        db.query(CompletionCertificate)
        .filter(CompletionCertificate.id == certificate_id)
        .first()
    )
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found.",
        )
    return _build_public_certificate_response(cert)


@router.post(
    "/verify",
    response_model=CertificateVerifyResponse,
    summary="Cryptographically verify a completion certificate",
)
def verify_certificate(
    request: CertificateVerifyRequest,
    db: Session = Depends(get_db),
):
    """
    Verifies the cryptographic integrity and authenticity of a certificate.
    Supports two verification paths:
    1. By certificate_id: Looks up the certificate in the database and verifies its signature.
    2. By client-supplied payload and signature: Reconstructs canonical payload, recomputes SHA-256 digest,
       and verifies Ed25519 signature against trusted public key for key_id.
    """
    # Path 1: Verify by Certificate UUID
    if request.certificate_id:
        cert = (
            db.query(CompletionCertificate)
            .filter(CompletionCertificate.id == request.certificate_id)
            .first()
        )
        if not cert:
            from datetime import datetime, timezone
            return CertificateVerifyResponse(
                is_valid=False,
                verification_status="NOT_FOUND",
                message=f"Certificate with ID '{request.certificate_id}' was not found.",
                certificate_id=request.certificate_id,
                verified_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )

        return certificate_service.verify_certificate(cert, db=db)

    # Path 2: Verify by provided payload and signature
    if request.payload is not None:
        cert_data = {
            "certificate_id": request.payload.get("certificate_id"),
            "schema_version": request.schema_version or request.payload.get("schema_version"),
            "key_id": request.key_id or request.payload.get("key_id"),
            "algorithm": request.algorithm or request.payload.get("algorithm", "ED25519-SHA256"),
            "payload": request.payload,
            "payload_digest": request.payload_digest,
            "signature": request.signature,
        }
        return certificate_service.verify_certificate(cert_data, db=db)

    from datetime import datetime, timezone
    return CertificateVerifyResponse(
        is_valid=False,
        verification_status="MALFORMED_CERTIFICATE",
        message="Verification request must provide either 'certificate_id' or 'payload' with 'signature'.",
        verified_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


@router.get(
    "/public-keys/list",
    response_model=List[PublicKeyInfo],
    summary="List trusted public keys for external verification",
)
def list_public_keys(
    db: Session = Depends(get_db),
):
    """
    Exports public keys (never private keys) for external and independent signature verification.
    """
    # Ensure active key is also registered
    try:
        active_key_id, active_priv = certificate_service.get_active_signing_key()
        pub_hex = active_priv.public_key().public_bytes_raw().hex()
        certificate_service.register_public_key(
            db=db,
            key_id=active_key_id,
            public_key_hex=pub_hex,
            description="Active signing key",
        )
    except Exception:
        pass

    keys = (
        db.query(CertificateSigningKey)
        .filter(CertificateSigningKey.is_active == True)
        .all()
    )
    return keys
