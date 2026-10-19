"""
Authoritative Subject Certificate Eligibility Service.

Provides a single, centralized source of truth for:
1. Student enrollment validity.
2. Required practical completion verification (authoritative ACCEPTED status + score >= threshold).
3. Progress percentage and remaining practicals calculation.
4. Active certificate status and pending request status.
5. Certification eligibility determination.

Used consistently across:
- Student academic progress endpoint (/certificates/student-progress)
- Student certificate request endpoint (/certificates/subject-requests)
- Faculty approval queue (/certificates/subject-approvals)
- Faculty review and final issuance (/certificates/subject-approvals/{request_id})
"""

from dataclasses import dataclass
from typing import List, Optional, Set
from sqlalchemy.orm import Session

from app.models.certificate import CompletionCertificate, SubjectCertificateRequest
from app.models.submission import Submission, SubmissionStatus
from app.models.university import Course, CourseEnrollment, Lab, LabPractical
from app.models.user import User, UserRole


@dataclass
class SubjectPracticalInfo:
    id: int
    title: str
    lab_id: int
    lab_title: str
    sequence_number: int
    is_required: bool
    passing_threshold: float
    is_completed: bool
    best_score: Optional[float]


@dataclass
class SubjectEligibilityResult:
    student_id: int
    course_id: int
    course_name: str
    course_code: str
    is_enrolled: bool
    total_required: int
    completed_required: int
    remaining_required: int
    completion_percentage: float
    is_eligible: bool
    eligibility_reason: str
    certificate_status: str  # "NOT_ELIGIBLE" | "ELIGIBLE" | "PENDING_APPROVAL" | "REJECTED" | "ISSUED"
    certificate_id: Optional[str]
    issued_at: Optional[str]
    request_id: Optional[int]
    rejection_note: Optional[str]
    required_practicals: List[SubjectPracticalInfo]
    incomplete_practical_titles: List[str]


def get_subject_certificate_eligibility(
    db: Session,
    student_id: int,
    course_id: int,
) -> SubjectEligibilityResult:
    """
    Authoritatively calculates subject certificate eligibility for a student.

    Rules:
    - Student must be actively enrolled in the course.
    - Course must be active.
    - All required practicals (is_required == True, is_active == True) across all active labs must be passed.
    - A practical is passed ONLY when an authoritative submission exists with:
      1. user_id == student_id
      2. practical_id == practical.id
      3. status == SubmissionStatus.ACCEPTED
      4. score >= practical.passing_threshold
    - If total_required == 0, the subject is NOT eligible for certification.
    - Optional practicals do not block certification.
    """
    course = db.query(Course).filter(Course.id == course_id, Course.is_active.isnot(False)).first()
    if not course:
        return SubjectEligibilityResult(
            student_id=student_id,
            course_id=course_id,
            course_name="Unknown Subject",
            course_code="",
            is_enrolled=False,
            total_required=0,
            completed_required=0,
            remaining_required=0,
            completion_percentage=0.0,
            is_eligible=False,
            eligibility_reason="Subject not found or inactive.",
            certificate_status="NOT_ELIGIBLE",
            certificate_id=None,
            issued_at=None,
            request_id=None,
            rejection_note=None,
            required_practicals=[],
            incomplete_practical_titles=[],
        )

    # 1. Verify enrollment
    enrollment = db.query(CourseEnrollment).filter(
        CourseEnrollment.course_id == course.id,
        CourseEnrollment.student_id == student_id,
        CourseEnrollment.status == "ENROLLED",
    ).first()
    is_enrolled = enrollment is not None

    # 2. Query labs and practicals
    lab_ids = [lab.id for lab in course.labs]
    if not lab_ids:
        return SubjectEligibilityResult(
            student_id=student_id,
            course_id=course.id,
            course_name=course.name,
            course_code=course.code or "",
            is_enrolled=is_enrolled,
            total_required=0,
            completed_required=0,
            remaining_required=0,
            completion_percentage=0.0,
            is_eligible=False,
            eligibility_reason="Subject has no laboratories configured.",
            certificate_status="NOT_ELIGIBLE",
            certificate_id=None,
            issued_at=None,
            request_id=None,
            rejection_note=None,
            required_practicals=[],
            incomplete_practical_titles=[],
        )

    # Filter by is_active if column exists on model
    practicals_query = db.query(LabPractical).filter(
        LabPractical.lab_id.in_(lab_ids),
        LabPractical.is_required.is_(True),
    )
    if hasattr(LabPractical, "is_active"):
        practicals_query = practicals_query.filter(LabPractical.is_active.isnot(False))

    required_practicals_orm = practicals_query.order_by(
        LabPractical.sequence_number.asc(),
        LabPractical.id.asc(),
    ).all()

    total_required = len(required_practicals_orm)

    # 3. Check passing submissions
    # Map practical_id -> best passing score
    completed_practical_ids: Set[int] = set()
    practical_scores: dict[int, float] = {}

    if total_required > 0 and is_enrolled:
        req_ids = [p.id for p in required_practicals_orm]
        # Query passing submissions for these practicals
        passing_subs = db.query(
            Submission.practical_id,
            Submission.score,
        ).filter(
            Submission.user_id == student_id,
            Submission.practical_id.in_(req_ids),
            Submission.status == SubmissionStatus.ACCEPTED,
        ).all()

        for sub_prac_id, sub_score in passing_subs:
            current_best = practical_scores.get(sub_prac_id, 0.0)
            if sub_score > current_best:
                practical_scores[sub_prac_id] = sub_score

        for p in required_practicals_orm:
            best_sc = practical_scores.get(p.id)
            threshold = p.passing_threshold if p.passing_threshold is not None else 100.0
            if best_sc is not None and best_sc >= threshold:
                completed_practical_ids.add(p.id)

    completed_required = len(completed_practical_ids)
    remaining_required = max(0, total_required - completed_required)
    completion_percentage = (
        round((completed_required / total_required) * 100.0, 1)
        if total_required > 0
        else 0.0
    )

    # Build practical info list
    practical_info_list: List[SubjectPracticalInfo] = []
    incomplete_titles: List[str] = []

    for p in required_practicals_orm:
        threshold = p.passing_threshold if p.passing_threshold is not None else 100.0
        is_done = p.id in completed_practical_ids
        title = (
            getattr(p, "effective_title", None)
            or getattr(p, "title", None)
            or (p.question.title if getattr(p, "question", None) else f"Practical #{p.sequence_number}")
        )
        if not is_done:
            incomplete_titles.append(title)

        lab_title = p.lab.title if p.lab else "Lab"
        practical_info_list.append(
            SubjectPracticalInfo(
                id=p.id,
                title=title,
                lab_id=p.lab_id,
                lab_title=lab_title,
                sequence_number=p.sequence_number,
                is_required=p.is_required,
                passing_threshold=threshold,
                is_completed=is_done,
                best_score=practical_scores.get(p.id),
            )
        )

    # 4. Check existing certificates and requests
    active_cert = db.query(CompletionCertificate).filter(
        CompletionCertificate.student_id == student_id,
        CompletionCertificate.course_id == course.id,
        CompletionCertificate.certificate_type == "SUBJECT",
        CompletionCertificate.status == "ACTIVE",
    ).first()

    existing_req = db.query(SubjectCertificateRequest).filter(
        SubjectCertificateRequest.student_id == student_id,
        SubjectCertificateRequest.course_id == course.id,
    ).first()

    # Academic eligibility: enrolled, subject has required practicals, and all are passed
    academically_eligible = (
        is_enrolled and total_required > 0 and completed_required >= total_required
    )

    # 5. Determine overall certificate status
    cert_id: Optional[str] = None
    issued_at_str: Optional[str] = None
    request_id: Optional[int] = None
    rejection_note: Optional[str] = None

    if active_cert:
        cert_status = "ISSUED"
        cert_id = active_cert.id
        issued_at_str = (
            active_cert.issued_at.isoformat()
            if hasattr(active_cert.issued_at, "isoformat")
            else str(active_cert.issued_at)
        )
        is_eligible = True
        eligibility_reason = "Certificate has already been issued."
    elif existing_req and existing_req.status == "PENDING":
        cert_status = "PENDING_APPROVAL"
        request_id = existing_req.id
        is_eligible = academically_eligible
        eligibility_reason = "A certificate request is currently pending faculty review."
    elif existing_req and existing_req.status == "REJECTED":
        cert_status = "REJECTED"
        request_id = existing_req.id
        rejection_note = existing_req.review_note
        is_eligible = academically_eligible
        if academically_eligible:
            eligibility_reason = "Requirements satisfied. Re-submission is permitted."
        else:
            eligibility_reason = f"Revision required: {len(incomplete_titles)} practicals incomplete."
    elif not is_enrolled:
        cert_status = "NOT_ELIGIBLE"
        is_eligible = False
        eligibility_reason = "Student is not enrolled in this subject."
    elif total_required == 0:
        cert_status = "NOT_ELIGIBLE"
        is_eligible = False
        eligibility_reason = "This subject has no required practical challenges."
    elif academically_eligible:
        cert_status = "ELIGIBLE"
        is_eligible = True
        eligibility_reason = "All required practicals completed. Eligible to request certificate."
    else:
        cert_status = "NOT_ELIGIBLE"
        is_eligible = False
        eligibility_reason = f"{remaining_required} required practical(s) still remaining."

    return SubjectEligibilityResult(
        student_id=student_id,
        course_id=course.id,
        course_name=course.name,
        course_code=course.code or "",
        is_enrolled=is_enrolled,
        total_required=total_required,
        completed_required=completed_required,
        remaining_required=remaining_required,
        completion_percentage=completion_percentage,
        is_eligible=is_eligible,
        eligibility_reason=eligibility_reason,
        certificate_status=cert_status,
        certificate_id=cert_id,
        issued_at=issued_at_str,
        request_id=request_id,
        rejection_note=rejection_note,
        required_practicals=practical_info_list,
        incomplete_practical_titles=incomplete_titles,
    )
