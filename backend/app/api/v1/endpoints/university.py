"""
University & Practical Laboratory Management Endpoints.
Implements Chunk 8 requirements for Courses, Labs, Practicals,
Faculty Assignments, and Student Enrollments with strict RBAC.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import (
    get_current_admin,
    get_current_faculty_or_admin,
    get_current_user,
    is_faculty_assigned_to_course,
    is_student_enrolled_in_course,
    verify_course_manage_permission,
    verify_course_view_permission,
    verify_lab_view_permission,
)
from app.core.database import get_db
from app.services.enrollment import (
    auto_enroll_student_in_matching_courses,
    auto_enroll_students_in_new_course,
)
from app.models.question import Question
from app.models.submission import Submission, SubmissionStatus
from app.models.university import (
    Course,
    CourseEnrollment,
    FacultyCourseAssignment,
    Lab,
    LabPractical,
)
from app.models.user import User, UserRole
from app.schemas.university import (
    CourseCreate,
    CourseEnrollmentRequest,
    CourseEnrollmentResponse,
    CourseResponse,
    CourseUpdate,
    FacultyAssignRequest,
    FacultyAssignmentResponse,
    LabCreate,
    LabPracticalCreate,
    LabPracticalResponse,
    LabPracticalUpdate,
    LabResponse,
    LabUpdate,
    PracticalUnlockStatus,
)

courses_router = APIRouter()
labs_router = APIRouter()
practicals_router = APIRouter()


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def build_course_response(course: Course, db: Session) -> CourseResponse:
    lab_count = db.query(Lab).filter(Lab.course_id == course.id).count()
    student_count = db.query(CourseEnrollment).filter(CourseEnrollment.course_id == course.id).count()
    faculty_count = db.query(FacultyCourseAssignment).filter(FacultyCourseAssignment.course_id == course.id).count()
    return CourseResponse(
        id=course.id,
        code=course.code,
        name=course.name,
        program=course.program,
        year_of_study=course.year_of_study,
        description=course.description,
        semester=course.semester,
        academic_year=course.academic_year,
        is_active=course.is_active,
        created_by=course.created_by,
        created_at=course.created_at,
        updated_at=course.updated_at,
        lab_count=lab_count,
        student_count=student_count,
        faculty_count=faculty_count,
        faculty_names=[
            assignment.faculty.name
            for assignment in db.query(FacultyCourseAssignment)
            .options(joinedload(FacultyCourseAssignment.faculty))
            .filter(FacultyCourseAssignment.course_id == course.id)
            .all()
            if assignment.faculty is not None
        ],
    )


def build_lab_response(lab: Lab, db: Session) -> LabResponse:
    practical_count = db.query(LabPractical).filter(LabPractical.lab_id == lab.id).count()
    return LabResponse(
        id=lab.id,
        course_id=lab.course_id,
        title=lab.title,
        description=lab.description,
        instructions=lab.instructions,
        display_order=lab.display_order,
        is_published=lab.is_published,
        created_by=lab.created_by,
        created_at=lab.created_at,
        updated_at=lab.updated_at,
        practical_count=practical_count,
    )


def build_practical_response(
    practical: LabPractical,
    status: PracticalUnlockStatus = PracticalUnlockStatus.AVAILABLE,
    is_unlocked: bool = True,
    best_score: Optional[float] = None,
    lock_reason: Optional[str] = None,
) -> LabPracticalResponse:
    q = practical.question
    effective_title = practical.title if practical.title and practical.title.strip() else (q.title if q else "Practical")
    return LabPracticalResponse(
        id=practical.id,
        lab_id=practical.lab_id,
        question_id=practical.question_id,
        question_title=q.title if q else None,
        question_slug=q.slug if q else None,
        question_difficulty=q.difficulty.value if q and hasattr(q.difficulty, "value") else (str(q.difficulty) if q else None),
        title=practical.title,
        instructions=practical.instructions,
        effective_title=effective_title,
        sequence_number=practical.sequence_number,
        is_required=practical.is_required,
        passing_threshold=practical.passing_threshold,
        status=status,
        is_unlocked=is_unlocked,
        best_score=best_score,
        lock_reason=lock_reason,
        created_at=practical.created_at,
        updated_at=practical.updated_at,
    )


def compute_practical_unlock_states(
    practicals: List[LabPractical],
    student_id: int,
    db: Session,
) -> List[LabPracticalResponse]:
    """
    Computes sequential unlocking state for a student across an ordered list of practicals in a lab.
    Rules:
    1. Practicals are evaluated in strict sequence order (sequence_number, id).
    2. A practical is COMPLETED if the student has at least one valid submission with score >= passing_threshold.
    3. The first required practical is initially AVAILABLE.
    4. Subsequent practicals are AVAILABLE only if all preceding required practicals are COMPLETED.
    5. Optional practicals do not block progression through required practicals.
    6. Repeated or later failed submissions never revoke an earned completion.
    """
    if not practicals:
        return []

    practical_ids = [p.id for p in practicals]
    submissions = (
        db.query(Submission)
        .filter(
            Submission.user_id == student_id,
            Submission.practical_id.in_(practical_ids),
        )
        .all()
    )

    # Group submissions by practical_id
    subs_by_practical: dict[int, list[Submission]] = {p.id: [] for p in practicals}
    for s in submissions:
        if s.practical_id in subs_by_practical:
            subs_by_practical[s.practical_id].append(s)

    # Assess completion & best scores
    is_completed: dict[int, bool] = {}
    best_scores: dict[int, Optional[float]] = {}
    for p in practicals:
        p_subs = subs_by_practical[p.id]
        if p_subs:
            best_scores[p.id] = max([s.score for s in p_subs], default=0.0)
            is_completed[p.id] = any(
                s.status not in (
                    SubmissionStatus.PENDING,
                    SubmissionStatus.RUNNING,
                    SubmissionStatus.COMPILATION_ERROR,
                    SubmissionStatus.RUNTIME_ERROR,
                    SubmissionStatus.TIME_LIMIT_EXCEEDED,
                    SubmissionStatus.INTERNAL_ERROR,
                )
                and s.score >= p.passing_threshold
                for s in p_subs
            )
        else:
            best_scores[p.id] = None
            is_completed[p.id] = False

    # Traverse sequence to assign unlock states
    responses: List[LabPracticalResponse] = []
    all_preceding_required_passed = True
    first_blocking_practical: Optional[LabPractical] = None

    for p in practicals:
        if is_completed[p.id]:
            resp = build_practical_response(
                p,
                status=PracticalUnlockStatus.COMPLETED,
                is_unlocked=True,
                best_score=best_scores[p.id],
                lock_reason=None,
            )
        elif all_preceding_required_passed:
            resp = build_practical_response(
                p,
                status=PracticalUnlockStatus.AVAILABLE,
                is_unlocked=True,
                best_score=best_scores[p.id],
                lock_reason=None,
            )
        else:
            blocking_name = first_blocking_practical.title or (
                first_blocking_practical.question.title if first_blocking_practical.question else "Preceding Practical"
            )
            reason = f"Complete Practical #{first_blocking_practical.sequence_number} ('{blocking_name}') first."
            resp = build_practical_response(
                p,
                status=PracticalUnlockStatus.LOCKED,
                is_unlocked=False,
                best_score=best_scores[p.id],
                lock_reason=reason,
            )

        responses.append(resp)

        # Preceding required check: only required practicals block progression
        if p.is_required and not is_completed[p.id]:
            if all_preceding_required_passed:
                all_preceding_required_passed = False
                first_blocking_practical = p

    return responses


# -----------------------------------------------------------------------------
# Courses Endpoints
# -----------------------------------------------------------------------------

@courses_router.post(
    "",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new course (Admin or Faculty)",
)
async def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_faculty_or_admin),
) -> CourseResponse:
    normalized_code = payload.code.strip().upper() if payload.code and payload.code.strip() else None
    if normalized_code:
        existing = db.query(Course).filter(Course.code == normalized_code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Subject code '{normalized_code}' is already in use.",
            )

    # Validate faculty before writing the subject so course + assignment are atomic.
    faculty_to_assign = None
    if payload.faculty_id is not None:
        faculty_to_assign = db.query(User).filter(User.id == payload.faculty_id).first()
        if not faculty_to_assign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected faculty member was not found.")
        if faculty_to_assign.role != UserRole.FACULTY or not faculty_to_assign.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Select an active faculty account.")
    elif current_user.role == UserRole.ADMIN:
        # API clients may omit this for backward compatibility, while the admin UI
        # requires an explicit selection.
        faculty_to_assign = None

    course = Course(
        code=normalized_code,
        name=payload.name.strip(),
        program=payload.program.strip(),
        year_of_study=payload.year_of_study.strip(),
        description=payload.description,
        semester=payload.semester.strip(),
        academic_year=payload.academic_year.strip() if payload.academic_year else None,
        is_active=payload.is_active,
        created_by=current_user.id,
    )
    db.add(course)
    db.flush()

    # Faculty-created subjects belong to that faculty member. Admin-created
    # subjects are assigned to the selected faculty member during creation.
    assigned_faculty = faculty_to_assign
    if current_user.role == UserRole.FACULTY:
        assigned_faculty = current_user
    if assigned_faculty is not None:
        db.add(FacultyCourseAssignment(
            course_id=course.id,
            faculty_id=assigned_faculty.id,
            assigned_by=current_user.id,
        ))

    db.commit()
    db.refresh(course)

    # Automatically scan students matching academic_year and semester and enroll them
    auto_enroll_students_in_new_course(course, db)

    return build_course_response(course, db)


@courses_router.get(
    "",
    response_model=List[CourseResponse],
    summary="List courses visible to the authenticated user",
)
async def list_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[CourseResponse]:
    query = db.query(Course)
    if current_user.role == UserRole.ADMIN:
        courses = query.order_by(Course.created_at.desc()).all()
    elif current_user.role == UserRole.FACULTY:
        assigned_course_ids = select(FacultyCourseAssignment.course_id).filter(FacultyCourseAssignment.faculty_id == current_user.id)
        courses = query.filter(Course.id.in_(assigned_course_ids)).order_by(Course.created_at.desc()).all()
    else:  # STUDENT
        # Auto-enroll student in matching courses if profile is completed
        auto_enroll_student_in_matching_courses(current_user, db)
        enrolled_course_ids = select(CourseEnrollment.course_id).filter(CourseEnrollment.student_id == current_user.id)
        courses = query.filter(Course.id.in_(enrolled_course_ids), Course.is_active.is_(True)).order_by(Course.created_at.desc()).all()

    return [build_course_response(c, db) for c in courses]


@courses_router.get(
    "/{course_id}",
    response_model=CourseResponse,
    summary="Get course details by ID",
)
async def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseResponse:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    verify_course_view_permission(course, current_user, db)
    return build_course_response(course, db)


@courses_router.patch(
    "/{course_id}",
    response_model=CourseResponse,
    summary="Update course (Admin or Assigned Faculty)",
)
async def update_course(
    course_id: int,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseResponse:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    verify_course_manage_permission(course, current_user, db)

    # Only admin can change course code
    if payload.code is not None:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only platform administrators can modify course codes.",
            )
        new_code = payload.code.strip().upper() if payload.code and payload.code.strip() else None
        if new_code != course.code:
            if new_code:
                existing = db.query(Course).filter(Course.code == new_code, Course.id != course.id).first()
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Subject code '{new_code}' is already used by another subject.",
                    )
            course.code = new_code

    if payload.name is not None:
        course.name = payload.name.strip()
    if payload.program is not None:
        course.program = payload.program.strip()
    if payload.year_of_study is not None:
        course.year_of_study = payload.year_of_study.strip()
    if payload.description is not None:
        course.description = payload.description
    if payload.semester is not None:
        course.semester = payload.semester.strip()
    if payload.academic_year is not None:
        course.academic_year = payload.academic_year.strip() if payload.academic_year else None
    if payload.is_active is not None:
        course.is_active = payload.is_active

    db.commit()
    db.refresh(course)
    return build_course_response(course, db)


@courses_router.get(
    "/{course_id}/deletion-preview",
    summary="Get course dependency summary before deletion (Admin only)",
)
async def get_course_deletion_preview(
    course_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    lab_ids = [l.id for l in course.labs]
    practical_count = db.query(LabPractical).filter(LabPractical.lab_id.in_(lab_ids)).count() if lab_ids else 0
    enrolled_count = len(course.enrollments)
    historical_subs = 0
    if lab_ids:
        practicals = db.query(LabPractical).filter(LabPractical.lab_id.in_(lab_ids)).all()
        question_ids = [p.question_id for p in practicals]
        enrolled_student_ids = [e.student_id for e in course.enrollments]
        if question_ids and enrolled_student_ids:
            historical_subs = (
                db.query(Submission)
                .filter(
                    Submission.question_id.in_(question_ids),
                    Submission.user_id.in_(enrolled_student_ids),
                )
                .count()
            )

    has_history = historical_subs > 0
    return {
        "course_id": course.id,
        "course_name": course.name,
        "course_code": course.code or "",
        "lab_count": len(course.labs),
        "practical_count": practical_count,
        "enrolled_student_count": enrolled_count,
        "historical_submissions_count": historical_subs,
        "has_historical_activity": has_history,
        "recommended_action": "ARCHIVE" if has_history else "HARD_DELETE",
        "warning_message": (
            f"This subject has {historical_subs} student submission(s). To protect historical academic integrity, "
            "it will be safely archived and deactivated rather than deleted."
            if has_history
            else "This subject has no recorded student submissions. It can be safely deleted."
        ),
    }


@courses_router.delete(
    "/{course_id}",
    summary="Delete or safely archive a course with dependency checks (Admin only)",
)
async def delete_course(
    course_id: int,
    archive_if_dependent: bool = False,
    archive: bool = False,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    should_archive = archive_if_dependent or archive
    lab_ids = [l.id for l in course.labs]
    historical_subs = 0
    if lab_ids:
        practicals = db.query(LabPractical).filter(LabPractical.lab_id.in_(lab_ids)).all()
        question_ids = [p.question_id for p in practicals]
        enrolled_student_ids = [e.student_id for e in course.enrollments]
        if question_ids and enrolled_student_ids:
            historical_subs = (
                db.query(Submission)
                .filter(
                    Submission.question_id.in_(question_ids),
                    Submission.user_id.in_(enrolled_student_ids),
                )
                .count()
            )

    if historical_subs > 0:
        if should_archive:
            course.is_active = False
            if lab_ids:
                db.query(LabPractical).filter(LabPractical.lab_id.in_(lab_ids)).update({"is_active": False}, synchronize_session=False)
            db.commit()
            return {
                "detail": f"Subject '{course.name}' has {historical_subs} historical candidate submissions. It was safely archived and deactivated to preserve historical academic integrity.",
                "archived": True,
                "id": course_id,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete course '{course.code}': {historical_subs} historical candidate submissions exist.",
            )

    db.delete(course)
    db.commit()
    return {"detail": f"Subject '{course.name}' deleted successfully.", "archived": False, "id": course_id}


@courses_router.get(
    "/{course_id}/default-lab",
    response_model=LabResponse,
    summary="Get or automatically create the primary laboratory for a course",
)
async def get_or_create_default_lab(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LabResponse:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    verify_course_manage_permission(course, current_user, db)

    existing_lab = db.query(Lab).filter(Lab.course_id == course.id).order_by(Lab.id.asc()).first()
    if existing_lab:
        return build_lab_response(existing_lab, db)

    default_lab = Lab(
        course_id=course.id,
        title=f"{course.name} Laboratory",
        description=f"Curriculum practicals and programming challenges for {course.name}",
        is_published=True,
        created_by=current_user.id,
    )
    db.add(default_lab)
    db.commit()
    db.refresh(default_lab)
    return build_lab_response(default_lab, db)


@courses_router.get(
    "/{course_id}/practicals",
    response_model=List[LabPracticalResponse],
    summary="List practicals for a course directly (Faculty / Admin)",
)
async def list_course_practicals(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[LabPracticalResponse]:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    verify_course_view_permission(course, current_user, db)

    lab_ids = [l.id for l in course.labs]
    if not lab_ids:
        return []

    practicals = (
        db.query(LabPractical)
        .options(joinedload(LabPractical.question))
        .filter(LabPractical.lab_id.in_(lab_ids))
        .order_by(LabPractical.sequence_number.asc(), LabPractical.id.asc())
        .all()
    )

    if current_user.role == UserRole.STUDENT:
        active_practicals = [p for p in practicals if getattr(p, "is_active", True)]
        return compute_practical_unlock_states(active_practicals, current_user.id, db)

    return [
        build_practical_response(
            p,
            status=PracticalUnlockStatus.AVAILABLE,
            is_unlocked=True,
            best_score=None,
            lock_reason=None,
        )
        for p in practicals
    ]


# -----------------------------------------------------------------------------
# Faculty Course Assignments
# -----------------------------------------------------------------------------

@courses_router.post(
    "/{course_id}/faculty",
    response_model=FacultyAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign faculty to course (Admin only)",
)
async def assign_faculty(
    course_id: int,
    payload: FacultyAssignRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> FacultyAssignmentResponse:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    faculty_user = db.query(User).filter(User.id == payload.faculty_id).first()
    if not faculty_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if faculty_user.role != UserRole.FACULTY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{faculty_user.email}' has role '{faculty_user.role}'. Only faculty members can be assigned.",
        )

    existing = (
        db.query(FacultyCourseAssignment)
        .filter(
            FacultyCourseAssignment.course_id == course_id,
            FacultyCourseAssignment.faculty_id == payload.faculty_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Faculty member is already assigned to this course.",
        )

    assignment = FacultyCourseAssignment(
        course_id=course_id,
        faculty_id=payload.faculty_id,
        assigned_by=admin.id,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return FacultyAssignmentResponse(
        id=assignment.id,
        course_id=assignment.course_id,
        faculty_id=assignment.faculty_id,
        faculty_name=faculty_user.name,
        faculty_email=faculty_user.email,
        assigned_at=assignment.assigned_at,
        assigned_by=assignment.assigned_by,
    )


@courses_router.get(
    "/{course_id}/faculty",
    response_model=List[FacultyAssignmentResponse],
    summary="List faculty assigned to course (Admin or Assigned Faculty)",
)
async def list_course_faculty(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[FacultyAssignmentResponse]:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    if current_user.role == UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students cannot access faculty assignment rosters.",
        )
    if current_user.role == UserRole.FACULTY and not is_faculty_assigned_to_course(course_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this course's faculty assignments.",
        )

    assignments = (
        db.query(FacultyCourseAssignment)
        .options(joinedload(FacultyCourseAssignment.faculty))
        .filter(FacultyCourseAssignment.course_id == course_id)
        .all()
    )
    return [
        FacultyAssignmentResponse(
            id=a.id,
            course_id=a.course_id,
            faculty_id=a.faculty_id,
            faculty_name=a.faculty.name if a.faculty else None,
            faculty_email=a.faculty.email if a.faculty else None,
            assigned_at=a.assigned_at,
            assigned_by=a.assigned_by,
        )
        for a in assignments
    ]


@courses_router.delete(
    "/{course_id}/faculty/{faculty_id}",
    summary="Revoke faculty assignment from course (Admin only)",
)
async def revoke_faculty_assignment(
    course_id: int,
    faculty_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    assignment = (
        db.query(FacultyCourseAssignment)
        .filter(
            FacultyCourseAssignment.course_id == course_id,
            FacultyCourseAssignment.faculty_id == faculty_id,
        )
        .first()
    )
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Faculty assignment not found for this course.",
        )

    db.delete(assignment)
    db.commit()
    return {"detail": "Faculty assignment revoked successfully.", "course_id": course_id, "faculty_id": faculty_id}


# -----------------------------------------------------------------------------
# Student Enrollments
# -----------------------------------------------------------------------------

@courses_router.post(
    "/{course_id}/enrollments",
    response_model=CourseEnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll student in course (Admin or Assigned Faculty)",
)
async def enroll_student(
    course_id: int,
    payload: CourseEnrollmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseEnrollmentResponse:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    verify_course_manage_permission(course, current_user, db)

    student_user = db.query(User).filter(User.id == payload.student_id).first()
    if not student_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if student_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{student_user.email}' has role '{student_user.role}'. Only students can be enrolled.",
        )

    existing = (
        db.query(CourseEnrollment)
        .filter(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == payload.student_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student is already enrolled in this course.",
        )

    enrollment = CourseEnrollment(
        course_id=course_id,
        student_id=payload.student_id,
        status=payload.status or "ENROLLED",
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)

    return CourseEnrollmentResponse(
        id=enrollment.id,
        course_id=enrollment.course_id,
        student_id=enrollment.student_id,
        student_name=student_user.name,
        student_email=student_user.email,
        enrolled_at=enrollment.enrolled_at,
        status=enrollment.status,
    )


@courses_router.get(
    "/{course_id}/enrollments",
    response_model=List[CourseEnrollmentResponse],
    summary="List enrolled students (Admin or Assigned Faculty)",
)
async def list_course_enrollments(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[CourseEnrollmentResponse]:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    if current_user.role == UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students cannot access class enrollment rosters.",
        )
    if current_user.role == UserRole.FACULTY and not is_faculty_assigned_to_course(course_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view enrollments for this course.",
        )

    enrollments = (
        db.query(CourseEnrollment)
        .options(joinedload(CourseEnrollment.student))
        .filter(CourseEnrollment.course_id == course_id)
        .all()
    )
    return [
        CourseEnrollmentResponse(
            id=e.id,
            course_id=e.course_id,
            student_id=e.student_id,
            student_name=e.student.name if e.student else None,
            student_email=e.student.email if e.student else None,
            enrolled_at=e.enrolled_at,
            status=e.status,
        )
        for e in enrollments
    ]


@courses_router.delete(
    "/{course_id}/enrollments/{student_id}",
    summary="Remove student enrollment (Admin or Assigned Faculty)",
)
async def remove_course_enrollment(
    course_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    verify_course_manage_permission(course, current_user, db)

    enrollment = (
        db.query(CourseEnrollment)
        .filter(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == student_id,
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment record not found for this student.",
        )

    db.delete(enrollment)
    db.commit()
    return {"detail": "Student unenrolled successfully.", "course_id": course_id, "student_id": student_id}


# -----------------------------------------------------------------------------
# Labs Endpoints
# -----------------------------------------------------------------------------

@courses_router.post(
    "/{course_id}/labs",
    response_model=LabResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a lab within a course (Admin or Assigned Faculty)",
)
async def create_lab(
    course_id: int,
    payload: LabCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LabResponse:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    verify_course_manage_permission(course, current_user, db)

    lab = Lab(
        course_id=course_id,
        title=payload.title.strip(),
        description=payload.description,
        instructions=payload.instructions,
        display_order=payload.display_order,
        is_published=payload.is_published,
        created_by=current_user.id,
    )
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return build_lab_response(lab, db)


@courses_router.get(
    "/{course_id}/labs",
    response_model=List[LabResponse],
    summary="List labs in a course (Admin, Assigned Faculty, or Enrolled Student)",
)
async def list_course_labs(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[LabResponse]:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    verify_course_view_permission(course, current_user, db)

    query = db.query(Lab).filter(Lab.course_id == course_id)
    if current_user.role == UserRole.STUDENT:
        query = query.filter(Lab.is_published.is_(True))

    labs = query.order_by(Lab.display_order.asc(), Lab.id.asc()).all()
    return [build_lab_response(l, db) for l in labs]


@labs_router.get(
    "/{lab_id}",
    response_model=LabResponse,
    summary="Get lab details by ID",
)
async def get_lab(
    lab_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LabResponse:
    lab = db.query(Lab).options(joinedload(Lab.course)).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab not found.")

    verify_lab_view_permission(lab, current_user, db)
    return build_lab_response(lab, db)


@labs_router.patch(
    "/{lab_id}",
    response_model=LabResponse,
    summary="Update lab (Admin or Assigned Faculty)",
)
async def update_lab(
    lab_id: int,
    payload: LabUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LabResponse:
    lab = db.query(Lab).options(joinedload(Lab.course)).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab not found.")

    verify_course_manage_permission(lab.course, current_user, db)

    if payload.title is not None:
        lab.title = payload.title.strip()
    if payload.description is not None:
        lab.description = payload.description
    if payload.instructions is not None:
        lab.instructions = payload.instructions
    if payload.display_order is not None:
        lab.display_order = payload.display_order
    if payload.is_published is not None:
        lab.is_published = payload.is_published

    db.commit()
    db.refresh(lab)
    return build_lab_response(lab, db)


@labs_router.delete(
    "/{lab_id}",
    summary="Delete lab with deletion safety checks (Admin or Assigned Faculty)",
)
async def delete_lab(
    lab_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lab = db.query(Lab).options(joinedload(Lab.course)).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab not found.")

    verify_course_manage_permission(lab.course, current_user, db)

    # Deletion safety check
    practicals = db.query(LabPractical).filter(LabPractical.lab_id == lab.id).all()
    question_ids = [p.question_id for p in practicals]
    if question_ids:
        enrolled_student_ids = select(CourseEnrollment.student_id).filter(CourseEnrollment.course_id == lab.course_id)
        historical_subs = (
            db.query(Submission)
            .filter(
                Submission.question_id.in_(question_ids),
                Submission.user_id.in_(enrolled_student_ids),
            )
            .count()
        )
        if historical_subs > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Cannot delete lab '{lab.title}': {historical_subs} candidate submissions exist "
                    "for practical questions in this lab. Unpublish the lab instead."
                ),
            )

    db.delete(lab)
    db.commit()
    return {"detail": f"Lab '{lab.title}' deleted successfully.", "id": lab_id}


# -----------------------------------------------------------------------------
# Lab Practicals Endpoints
# -----------------------------------------------------------------------------

@labs_router.post(
    "/{lab_id}/practicals",
    response_model=LabPracticalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an ordered practical to a lab (Admin or Assigned Faculty)",
)
async def create_practical(
    lab_id: int,
    payload: LabPracticalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LabPracticalResponse:
    lab = db.query(Lab).options(joinedload(Lab.course)).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab not found.")

    verify_course_manage_permission(lab.course, current_user, db)

    # Validate that question exists
    question = db.query(Question).filter(Question.id == payload.question_id).first()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Referenced Question with ID {payload.question_id} was not found in the question catalog.",
        )

    # Prevent duplicate question within the same lab
    existing_q = (
        db.query(LabPractical)
        .filter(
            LabPractical.lab_id == lab_id,
            LabPractical.question_id == payload.question_id,
        )
        .first()
    )
    if existing_q:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Question with ID {payload.question_id} is already assigned to this lab (sequence #{existing_q.sequence_number}).",
        )

    # Auto-assign sequence position if omitted
    target_seq = payload.sequence_number
    if target_seq is None:
        max_seq = db.query(func.max(LabPractical.sequence_number)).filter(LabPractical.lab_id == lab_id).scalar()
        target_seq = (max_seq or 0) + 1
    else:
        # Prevent duplicate sequence position within the same lab
        existing_seq = (
            db.query(LabPractical)
            .filter(
                LabPractical.lab_id == lab_id,
                LabPractical.sequence_number == target_seq,
            )
            .first()
        )
        if existing_seq:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Sequence number {target_seq} is already occupied in this lab.",
            )

    prac_title = (payload.title or payload.effective_title or "").strip() or None

    practical = LabPractical(
        lab_id=lab_id,
        question_id=payload.question_id,
        title=prac_title,
        instructions=payload.instructions,
        sequence_number=target_seq,
        is_required=payload.is_required,
        passing_threshold=payload.passing_threshold,
    )
    db.add(practical)
    db.commit()
    db.refresh(practical)

    practical.question = question
    return build_practical_response(practical)


@courses_router.post(
    "/{course_id}/practicals",
    response_model=LabPracticalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and attach practical directly to course default laboratory (Faculty / Admin)",
)
async def create_course_practical_direct(
    course_id: int,
    payload: LabPracticalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LabPracticalResponse:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    verify_course_manage_permission(course, current_user, db)

    # Get or create default lab
    default_lab = db.query(Lab).filter(Lab.course_id == course.id).order_by(Lab.id.asc()).first()
    if not default_lab:
        default_lab = Lab(
            course_id=course.id,
            title=f"{course.name} Laboratory",
            description=f"Curriculum practicals and programming challenges for {course.name}",
            is_published=True,
            created_by=current_user.id,
        )
        db.add(default_lab)
        db.commit()
        db.refresh(default_lab)

    return await create_practical(lab_id=default_lab.id, payload=payload, db=db, current_user=current_user)


@labs_router.get(
    "/{lab_id}/practicals",
    response_model=List[LabPracticalResponse],
    summary="List ordered practicals in a lab (Authorized Course Members)",
)
async def list_lab_practicals(
    lab_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[LabPracticalResponse]:
    lab = db.query(Lab).options(joinedload(Lab.course)).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lab not found.")

    verify_lab_view_permission(lab, current_user, db)

    practicals = (
        db.query(LabPractical)
        .options(joinedload(LabPractical.question))
        .filter(LabPractical.lab_id == lab_id)
        .order_by(LabPractical.sequence_number.asc(), LabPractical.id.asc())
        .all()
    )
    if current_user.role == UserRole.STUDENT:
        return compute_practical_unlock_states(practicals, current_user.id, db)
    return [
        build_practical_response(
            p,
            status=PracticalUnlockStatus.AVAILABLE,
            is_unlocked=True,
            best_score=None,
            lock_reason=None,
        )
        for p in practicals
    ]


@practicals_router.get(
    "/{practical_id}",
    response_model=LabPracticalResponse,
    summary="Get practical details and status (Authorized Course Members)",
)
async def get_practical(
    practical_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LabPracticalResponse:
    practical = (
        db.query(LabPractical)
        .options(joinedload(LabPractical.lab).joinedload(Lab.course), joinedload(LabPractical.question))
        .filter(LabPractical.id == practical_id)
        .first()
    )
    if not practical:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practical not found.")

    verify_lab_view_permission(practical.lab, current_user, db)

    if current_user.role == UserRole.STUDENT:
        lab_practicals = (
            db.query(LabPractical)
            .options(joinedload(LabPractical.question))
            .filter(LabPractical.lab_id == practical.lab_id)
            .order_by(LabPractical.sequence_number.asc(), LabPractical.id.asc())
            .all()
        )
        states = compute_practical_unlock_states(lab_practicals, current_user.id, db)
        target_state = next((s for s in states if s.id == practical.id), None)
        if not target_state or not target_state.is_unlocked:
            reason = target_state.lock_reason if (target_state and target_state.lock_reason) else "Complete preceding required practicals first."
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Practical is locked. {reason}",
            )
        return target_state

    return build_practical_response(practical, status=PracticalUnlockStatus.AVAILABLE, is_unlocked=True)


@practicals_router.patch(
    "/{practical_id}",
    response_model=LabPracticalResponse,
    summary="Update practical configuration (Admin or Assigned Faculty)",
)
async def update_practical(
    practical_id: int,
    payload: LabPracticalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> LabPracticalResponse:
    practical = (
        db.query(LabPractical)
        .options(joinedload(LabPractical.lab).joinedload(Lab.course), joinedload(LabPractical.question))
        .filter(LabPractical.id == practical_id)
        .first()
    )
    if not practical:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practical not found.")

    verify_course_manage_permission(practical.lab.course, current_user, db)

    if payload.sequence_number is not None and payload.sequence_number != practical.sequence_number:
        seq_conflict = (
            db.query(LabPractical)
            .filter(
                LabPractical.lab_id == practical.lab_id,
                LabPractical.sequence_number == payload.sequence_number,
                LabPractical.id != practical.id,
            )
            .first()
        )
        if seq_conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Sequence position {payload.sequence_number} is already occupied in this lab.",
            )
        practical.sequence_number = payload.sequence_number

    if payload.title is not None:
        practical.title = payload.title.strip() if payload.title.strip() else None
    if payload.instructions is not None:
        practical.instructions = payload.instructions
    if payload.is_required is not None:
        practical.is_required = payload.is_required
    if payload.passing_threshold is not None:
        if payload.passing_threshold < 0.0 or payload.passing_threshold > 100.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passing threshold must be between 0.0 and 100.0 percent.",
            )
        practical.passing_threshold = payload.passing_threshold

    db.commit()
    db.refresh(practical)
    return build_practical_response(practical)


@practicals_router.get(
    "/{practical_id}/deletion-preview",
    summary="Preview practical deletion implications (Admin or Assigned Faculty)",
)
async def preview_practical_deletion(
    practical_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    practical = (
        db.query(LabPractical)
        .options(joinedload(LabPractical.lab).joinedload(Lab.course))
        .filter(LabPractical.id == practical_id)
        .first()
    )
    if not practical:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practical not found.")

    verify_course_manage_permission(practical.lab.course, current_user, db)

    enrolled_student_ids = select(CourseEnrollment.student_id).filter(CourseEnrollment.course_id == practical.lab.course_id)
    historical_subs = (
        db.query(Submission)
        .filter(
            (Submission.practical_id == practical.id)
            | (
                (Submission.question_id == practical.question_id)
                & Submission.user_id.in_(enrolled_student_ids)
            )
        )
        .count()
    )

    has_history = historical_subs > 0
    return {
        "practical_id": practical.id,
        "title": getattr(practical, "effective_title", None) or getattr(practical, "title", None) or (practical.question.title if getattr(practical, "question", None) else "Practical"),
        "subject_name": practical.lab.course.name if practical.lab and practical.lab.course else "Subject",
        "lab_title": practical.lab.title if practical.lab else "Lab",
        "historical_submissions_count": historical_subs,
        "has_historical_activity": has_history,
        "action": "ARCHIVE" if has_history else "HARD_DELETE",
        "warning_message": (
            f"This practical has {historical_subs} student submission(s). To protect historical student work and badges, "
            "it will be safely archived rather than deleted. Students will no longer see it in active assignments."
            if has_history
            else "This practical has no recorded student submissions. It will be permanently removed from the lab."
        ),
    }


@practicals_router.delete(
    "/{practical_id}",
    summary="Remove or safely archive practical from lab (Admin or Assigned Faculty)",
)
async def delete_practical(
    practical_id: int,
    archive_if_dependent: bool = False,
    archive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    practical = (
        db.query(LabPractical)
        .options(joinedload(LabPractical.lab).joinedload(Lab.course))
        .filter(LabPractical.id == practical_id)
        .first()
    )
    if not practical:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practical not found.")

    verify_course_manage_permission(practical.lab.course, current_user, db)

    should_archive = archive_if_dependent or archive
    enrolled_student_ids = select(CourseEnrollment.student_id).filter(CourseEnrollment.course_id == practical.lab.course_id)
    historical_subs = (
        db.query(Submission)
        .filter(
            (Submission.practical_id == practical.id)
            | (
                (Submission.question_id == practical.question_id)
                & Submission.user_id.in_(enrolled_student_ids)
            )
        )
        .count()
    )

    if historical_subs > 0:
        if should_archive:
            practical.is_active = False
            db.commit()
            return {
                "detail": f"Practical '{practical.title or practical.id}' had {historical_subs} student submission(s) and was safely archived. Historical submissions and badges remain intact.",
                "archived": True,
                "id": practical_id,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete practical sequence #{practical.sequence_number}: {historical_subs} candidate submissions exist.",
            )

    db.delete(practical)
    db.commit()
    return {"detail": "Practical removed from lab successfully.", "archived": False, "id": practical_id}
