"""
Submission & Automated Grading API Endpoints (Chunk 7).
Provides authenticated submission ingestion, automated evaluation execution,
paginated submission history retrieval, and granular test result viewing.
"""

from datetime import datetime, timezone
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin, get_current_user
from app.core.database import get_db
from app.models.question import Question, QuestionStatus
from app.models.submission import Submission, SubmissionStatus, SubmissionTestResult, TestCase
from app.models.university import CourseEnrollment, Lab, LabPractical, FacultyCourseAssignment
from app.models.user import User, UserRole
from app.models.certificate import CertificateApprovalRequest
from app.schemas.submission import (
    SubmissionCreateRequest,
    SubmissionListItem,
    SubmissionListResponse,
    SubmissionResponse,
    SubmissionTestResultResponse,
)
from app.services.grading import (
    build_safe_submission_response,
    format_safe_test_result,
    grading_service,
)

logger = logging.getLogger("secure_coding_platform.endpoints.submissions")

router = APIRouter()


@router.post(
    "",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit solution for automated grading",
    description=(
        "Submits source code for an existing question, evaluates it against authoritative "
        "backend test cases, and persists the permanent submission record."
    ),
)
async def create_submission(
    payload: SubmissionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubmissionResponse:
    """
    Submits code for evaluation.
    Security:
    - User identity is strictly derived from the authenticated JWT session.
    - Question must exist and be accessible.
    - Language must be supported by the question (if languages are constrained).
    - Checks for authoritative backend test cases before grading.
    - Runs grading pipeline through Judge0 service.
    - Persists permanent submission and individual test results.
    - Returns sanitized response protecting hidden test cases.
    """
    logger.info(
        f"Submission initiated by user_id={current_user.id} for question_id={payload.question_id} "
        f"using language={payload.language}"
    )

    # 1. Verify question exists
    question = (
        db.query(Question)
        .options(joinedload(Question.languages), joinedload(Question.test_cases))
        .filter(Question.id == payload.question_id)
        .first()
    )
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID {payload.question_id} was not found.",
        )

    # If student, question must be PUBLISHED
    if current_user.role != UserRole.ADMIN and question.status != QuestionStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with ID {payload.question_id} is not available for submissions.",
        )

    # 2. Verify language is allowed for this question (if language restrictions exist)
    if question.languages:
        allowed_langs = [ql.language.lower() for ql in question.languages]
        if payload.language.lower() not in allowed_langs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Language '{payload.language}' is not permitted for this question. "
                    f"Allowed: {', '.join(allowed_langs)}"
                ),
            )

    # 3. Verify authoritative test cases exist
    if not question.test_cases:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This problem does not have any configured grading test cases. "
                "Submissions cannot be evaluated until an administrator configures test cases."
            ),
        )

    # 4. If practical_id is supplied, validate university practical relationship & sequential unlock state
    if payload.practical_id is not None:
        practical = (
            db.query(LabPractical)
            .options(joinedload(LabPractical.lab).joinedload(Lab.course))
            .filter(LabPractical.id == payload.practical_id)
            .first()
        )
        if not practical:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Practical with ID {payload.practical_id} was not found.",
            )

        # Validate that the practical references the target question
        if practical.question_id != payload.question_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Practical with ID {practical.id} references question {practical.question_id}, "
                    f"which does not match the submitted question {payload.question_id}."
                ),
            )

        # Student-specific authorization & sequential unlocking check
        if current_user.role == UserRole.STUDENT:
            # Check student enrollment in the course that contains this lab
            enrollment = (
                db.query(CourseEnrollment)
                .filter(
                    CourseEnrollment.course_id == practical.lab.course_id,
                    CourseEnrollment.student_id == current_user.id,
                )
                .first()
            )
            if not enrollment:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You are not enrolled in the course that contains this practical lab.",
                )

            # Check that lab is published
            if not practical.lab.is_published:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Lab is not published.",
                )

            # Check sequential unlocking: verify that all preceding required practicals in this lab have passed
            preceding_required = (
                db.query(LabPractical)
                .filter(
                    LabPractical.lab_id == practical.lab_id,
                    LabPractical.is_required == True,
                    (
                        (LabPractical.sequence_number < practical.sequence_number)
                        | (
                            (LabPractical.sequence_number == practical.sequence_number)
                            & (LabPractical.id < practical.id)
                        )
                    ),
                )
                .order_by(LabPractical.sequence_number.asc(), LabPractical.id.asc())
                .all()
            )

            for prec in preceding_required:
                # Check whether current student has a passing submission for this preceding practical
                prec_pass = (
                    db.query(Submission)
                    .filter(
                        Submission.user_id == current_user.id,
                        Submission.practical_id == prec.id,
                        Submission.status.notin_([
                            SubmissionStatus.PENDING,
                            SubmissionStatus.RUNNING,
                            SubmissionStatus.COMPILATION_ERROR,
                            SubmissionStatus.RUNTIME_ERROR,
                            SubmissionStatus.TIME_LIMIT_EXCEEDED,
                            SubmissionStatus.INTERNAL_ERROR,
                        ]),
                        Submission.score >= prec.passing_threshold,
                    )
                    .first()
                )
                if not prec_pass:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=(
                            f"Practical sequence #{practical.sequence_number} is locked. "
                            f"You must complete preceding required practical sequence #{prec.sequence_number} first."
                        ),
                    )

    # 5. Check for accidental rapid duplicate submission (e.g. double-click within 2s with identical code)
    recent_sub = (
        db.query(Submission)
        .filter(
            Submission.user_id == current_user.id,
            Submission.question_id == question.id,
            Submission.practical_id == payload.practical_id,
        )
        .order_by(Submission.id.desc())
        .first()
    )
    if (
        recent_sub
        and recent_sub.source_code == payload.source_code
        and recent_sub.language == payload.language.lower()
        and recent_sub.status not in (SubmissionStatus.PENDING, SubmissionStatus.RUNNING)
    ):
        created_time = recent_sub.created_at
        if created_time is not None:
            if created_time.tzinfo is None:
                created_time = created_time.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - created_time).total_seconds()
            if 0.0 <= elapsed < 2.0:
                final_submission = (
                    db.query(Submission)
                    .options(
                        joinedload(Submission.test_results).joinedload(SubmissionTestResult.test_case)
                    )
                    .filter(Submission.id == recent_sub.id)
                    .first()
                )
                if final_submission:
                    return build_safe_submission_response(final_submission, include_source=True)

    # 6. Create initial Submission record in PENDING state
    submission = Submission(
        user_id=current_user.id,
        question_id=question.id,
        practical_id=payload.practical_id,
        language=payload.language.lower(),
        source_code=payload.source_code,
        status=SubmissionStatus.PENDING,
        total_test_cases=len(question.test_cases),
        passed_test_cases=0,
        score=0.0,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # 6. Execute automated grading pipeline
    evaluated_submission = await grading_service.evaluate_submission(db, submission)

    # Automatic practical badge award
    if current_user.role == UserRole.STUDENT and payload.practical_id is not None:
        practical = db.query(LabPractical).filter(LabPractical.id == payload.practical_id).first()
        if practical and evaluated_submission.status == SubmissionStatus.ACCEPTED and evaluated_submission.score >= practical.passing_threshold:
            from app.services.badge_service import award_badge_if_eligible
            award_badge_if_eligible(db, current_user.id, practical, evaluated_submission)

    # Re-fetch with test results and test cases eagerly loaded for safe serialization
    final_submission = (
        db.query(Submission)
        .options(
            joinedload(Submission.test_results).joinedload(SubmissionTestResult.test_case)
        )
        .filter(Submission.id == evaluated_submission.id)
        .first()
    )

    return build_safe_submission_response(final_submission, include_source=True)


@router.get(
    "",
    response_model=SubmissionListResponse,
    summary="Get authenticated user's submission history",
    description="Returns a paginated list of submissions belonging strictly to the authenticated user.",
)
async def list_submissions(
    question_id: Optional[int] = Query(None, description="Optional filter by question ID"),
    practical_id: Optional[int] = Query(None, description="Optional filter by practical ID"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubmissionListResponse:
    """
    Returns the authenticated user's submission history.
    Enforces user isolation: students can NEVER view other students' submissions.
    Omits full source code to minimize network payload and avoid data leakage.
    """
    query = db.query(Submission).filter(Submission.user_id == current_user.id)

    if question_id is not None:
        query = query.filter(Submission.question_id == question_id)

    if practical_id is not None:
        query = query.filter(Submission.practical_id == practical_id)

    total = query.count()
    pages = (total + page_size - 1) // page_size if total > 0 else 1
    offset = (page - 1) * page_size

    submissions = (
        query.order_by(Submission.created_at.desc(), Submission.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = [
        SubmissionListItem(
            id=s.id,
            user_id=s.user_id,
            question_id=s.question_id,
            practical_id=s.practical_id,
            language=s.language,
            status=s.status,
            total_test_cases=s.total_test_cases,
            passed_test_cases=s.passed_test_cases,
            score=s.score,
            execution_time_ms=s.execution_time_ms,
            memory_kb=s.memory_kb,
            error_message=s.error_message,
            created_at=s.created_at,
        )
        for s in submissions
    ]

    return SubmissionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/faculty/list",
    summary="List submissions for courses assigned to the authenticated faculty member",
)
async def list_faculty_submissions(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.ADMIN:
        query = db.query(Submission)
    elif current_user.role == UserRole.FACULTY:
        assigned_course_ids = db.query(FacultyCourseAssignment.course_id).filter(FacultyCourseAssignment.faculty_id == current_user.id)
        assigned_lab_ids = db.query(Lab.id).filter(Lab.course_id.in_(assigned_course_ids))
        assigned_practical_ids = db.query(LabPractical.id).filter(LabPractical.lab_id.in_(assigned_lab_ids))
        query = db.query(Submission).filter(Submission.practical_id.in_(assigned_practical_ids))
    else:
        raise HTTPException(status_code=403, detail="Faculty access required.")
    total = query.count()
    items = query.order_by(Submission.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [{"id": x.id, "user_id": x.user_id, "student_name": x.user.name if x.user else "Student", "question_id": x.question_id, "question_title": x.question.title if x.question else "Practical", "practical_id": x.practical_id, "language": x.language, "status": x.status.value if hasattr(x.status, "value") else str(x.status), "total_test_cases": x.total_test_cases, "passed_test_cases": x.passed_test_cases, "score": x.score, "created_at": x.created_at} for x in items], "total": total, "page": page, "page_size": page_size}


@router.get(
    "/admin/list",
    response_model=SubmissionListResponse,
    summary="List submissions across the platform (Admin only)",
    description="Returns a paginated, metadata-only view of platform submissions. Source code and test inputs are excluded.",
)
async def list_all_submissions_admin(
    user_id: Optional[int] = Query(None, ge=1),
    question_id: Optional[int] = Query(None, ge=1),
    status_filter: Optional[SubmissionStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> SubmissionListResponse:
    """Administrative cross-user view with server-side filters and pagination."""
    query = db.query(Submission)
    if user_id is not None:
        query = query.filter(Submission.user_id == user_id)
    if question_id is not None:
        query = query.filter(Submission.question_id == question_id)
    if status_filter is not None:
        query = query.filter(Submission.status == status_filter)

    total = query.count()
    pages = (total + page_size - 1) // page_size if total else 1
    items = (
        query.order_by(Submission.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return SubmissionListResponse(
        items=[
            SubmissionListItem(
                id=item.id,
                user_id=item.user_id,
                question_id=item.question_id,
                practical_id=item.practical_id,
                language=item.language,
                status=item.status,
                total_test_cases=item.total_test_cases,
                passed_test_cases=item.passed_test_cases,
                score=item.score,
                execution_time_ms=item.execution_time_ms,
                memory_kb=item.memory_kb,
                error_message=item.error_message,
                created_at=item.created_at,
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{submission_id}",
    response_model=SubmissionResponse,
    summary="Get single submission details",
    description="Returns submission details including source code and sanitized test case outcomes.",
)
async def get_submission(
    submission_id: int,
    practical_id: Optional[int] = Query(None, description="Optional practical ID to validate against"),
    question_id: Optional[int] = Query(None, description="Optional question ID to validate against"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubmissionResponse:
    """
    Retrieves full details of a submission.
    Ownership enforcement:
    - Candidate can only access their own submissions.
    - Admins may inspect candidate submissions for grading audit.
    - Hidden test case inputs and expected outputs are strictly obscured.
    - If practical_id or question_id are specified, validates that the submission matches.
    """
    submission = (
        db.query(Submission)
        .options(
            joinedload(Submission.test_results).joinedload(SubmissionTestResult.test_case)
        )
        .filter(Submission.id == submission_id)
        .first()
    )

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission with ID {submission_id} was not found.",
        )

    # Ownership check
    if submission.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this submission.",
        )

    # Challenge validation (CASE 9)
    if practical_id is not None and submission.practical_id != practical_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Submission with ID {submission_id} does not belong to practical {practical_id}.",
        )
    if question_id is not None and submission.question_id != question_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Submission with ID {submission_id} does not belong to question {question_id}.",
        )

    return build_safe_submission_response(submission, include_source=True)


@router.get(
    "/{submission_id}/results",
    response_model=List[SubmissionTestResultResponse],
    summary="Get individual test case results for a submission",
    description="Returns safe, permitted test case outcomes for a submission owned by the authenticated user.",
)
async def get_submission_results(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[SubmissionTestResultResponse]:
    """
    Returns individual test results for a submission.
    Security:
    - Ownership verified against authenticated user.
    - Hidden test inputs and expected outputs are never returned.
    """
    submission = (
        db.query(Submission)
        .options(
            joinedload(Submission.test_results).joinedload(SubmissionTestResult.test_case)
        )
        .filter(Submission.id == submission_id)
        .first()
    )

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission with ID {submission_id} was not found.",
        )

    # Ownership check
    if submission.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view test results for this submission.",
        )

    safe_results = []
    for res in submission.test_results:
        safe_results.append(format_safe_test_result(res, res.test_case))

    return safe_results


@router.get("/{submission_id}/feedback", summary="Get AI-assisted feedback for the authenticated user's submission")
async def get_submission_feedback(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import httpx
    from app.core.config import settings

    submission = db.query(Submission).options(joinedload(Submission.question)).filter(Submission.id == submission_id).first()
    if not submission or (current_user.role == UserRole.STUDENT and submission.user_id != current_user.id):
        raise HTTPException(status_code=404, detail="Submission not found.")
    if current_user.role == UserRole.FACULTY:
        practical = db.query(LabPractical).options(joinedload(LabPractical.lab)).filter(LabPractical.id == submission.practical_id).first() if submission.practical_id else None
        assigned = practical and db.query(FacultyCourseAssignment.id).filter(FacultyCourseAssignment.course_id == practical.lab.course_id, FacultyCourseAssignment.faculty_id == current_user.id).first()
        if not assigned:
            raise HTTPException(status_code=403, detail="You are not assigned to this submission's subject.")
    if not settings.AI_API_KEY:
        raise HTTPException(status_code=503, detail="AI feedback is not configured. Add AI_API_KEY to backend/.env.")
    q = submission.question
    prompt = f"Give concise, constructive programming feedback for this student's solution. Do not reveal hidden test inputs or expected outputs. State likely issue(s), one actionable improvement, and a short concept explanation. Do not claim a test passed unless the platform result says so.\nProblem: {q.title if q else 'Programming problem'}\nStatement: {q.description if q else ''}\nEvaluation: {submission.status.value if hasattr(submission.status, 'value') else submission.status}; {submission.passed_test_cases}/{submission.total_test_cases} tests passed; score {submission.score}%.\nLanguage: {submission.language}\nSource code:\n{submission.source_code[:12000]}"
    base_url = settings.AI_BASE_URL.rstrip("/")
    url = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(url, headers={"Authorization": f"Bearer {settings.AI_API_KEY}", "Content-Type": "application/json"}, json={"model": settings.AI_MODEL, "temperature": 0.2, "messages": [{"role": "system", "content": "You are a supportive programming tutor. Ground feedback in the provided source and evaluation data."}, {"role": "user", "content": prompt}]})
            response.raise_for_status()
            feedback = response.json()["choices"][0]["message"]["content"]
        return {"submission_id": submission.id, "feedback": feedback, "source": "ai_assisted", "evaluation_status": submission.status.value if hasattr(submission.status, "value") else str(submission.status)}
    except HTTPException:
        raise

    except httpx.TimeoutException:
        print("AI feedback error: The provider request timed out.")

        raise HTTPException(
            status_code=504,
            detail="The AI provider timed out. Please try again."
        ) from None

    except httpx.HTTPStatusError as exc:
        # Log the provider's HTTP status and a limited response body.
        # Never log request headers, API keys, or authorization tokens.
        print(f"AI provider HTTP status: {exc.response.status_code}")
        print(f"AI provider response: {exc.response.text[:1000]}")

        raise HTTPException(
            status_code=502,
            detail="The AI provider rejected or could not process the request. Check the backend logs."
        ) from None

    except httpx.RequestError as exc:
        print(f"AI provider connection error: {type(exc).__name__}")

        raise HTTPException(
            status_code=502,
            detail="Could not connect to the AI provider. Check the backend logs."
        ) from None

    except (KeyError, IndexError, TypeError, ValueError) as exc:
        print(f"AI provider returned an unexpected response: {type(exc).__name__}")

        raise HTTPException(
            status_code=502,
            detail="The AI provider returned an unexpected response."
        ) from None

    except Exception as exc:
        print(f"Unexpected AI feedback error: {type(exc).__name__}")

        raise HTTPException(
            status_code=502,
            detail="AI feedback failed unexpectedly. Check the backend logs."
        ) from None
