"""
Administrative User Management Endpoints.
Allows administrators to inspect user accounts and manage role assignments.
Strictly secured to platform administrators only.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_super_admin, get_current_user
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import (
    AdminStudentAcademicProfileUpdateRequest,
    StudentProfileUpdateRequest,
    UserResponse,
)

from app.models.university import Course, CourseEnrollment, FacultyCourseAssignment

router = APIRouter()


class RoleUpdateRequest(BaseModel):
    role: UserRole


@router.get(
    "",
    response_model=List[UserResponse],
    summary="List users filtered by role (Admin only)",
)
async def list_users(
    role: Optional[str] = Query(None, description="Optional role filter: STUDENT, FACULTY, ADMIN"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> List[UserResponse]:
    query = db.query(User)
    if role:
        try:
            role_enum = UserRole(role.upper())
            query = query.filter(User.role == role_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role filter '{role}'. Valid options: STUDENT, FACULTY, ADMIN",
            )

    users = query.order_by(User.name.asc()).all()
    result = []
    for u in users:
        u_resp = UserResponse.model_validate(u)
        if u.role == UserRole.FACULTY:
            assignments = (
                db.query(Course.code, Course.name)
                .join(FacultyCourseAssignment, FacultyCourseAssignment.course_id == Course.id)
                .filter(FacultyCourseAssignment.faculty_id == u.id)
                .all()
            )
            u_resp.assigned_courses = [f"{c.code or 'No code'} - {c.name}" for c in assignments]
        elif u.role == UserRole.STUDENT:
            enrollments = (
                db.query(Course.code, Course.name)
                .join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
                .filter(CourseEnrollment.student_id == u.id)
                .all()
            )
            u_resp.enrolled_courses = [f"{c.code or 'No code'} - {c.name}" for c in enrollments]
        result.append(u_resp)
    return result


@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Update user role (Admin only)",
)
async def update_user_role(
    user_id: int,
    payload: RoleUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_super_admin),
) -> UserResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # Public/ordinary role editing must never create an administrator account.
    # Administrator registration is controlled by the enrollment allowlist and
    # explicit admin_job_role provisioning instead.
    if payload.role == UserRole.ADMIN and user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Promoting an account to ADMIN is not supported here. Provision an authorized enrollment and use the administrator registration flow.",
        )

    if user.role == UserRole.ADMIN and payload.role != UserRole.ADMIN and user.is_active:
        admin_count = db.query(User).filter(
            User.role == UserRole.ADMIN,
            User.is_active.is_(True),
        ).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the sole active administrator account.",
            )

    if (user.admin_job_role or "").strip().upper() == "SUPER_ADMIN" and payload.role != UserRole.ADMIN and user.is_active:
        super_admin_count = db.query(User).filter(
            User.role == UserRole.ADMIN,
            User.is_active.is_(True),
            User.admin_job_role == "SUPER_ADMIN",
        ).count()
        if super_admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last active SUPER_ADMIN account.",
            )

    user.role = payload.role
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.patch(
    "/me/academic-profile",
    response_model=UserResponse,
    summary="Update authenticated student academic profile and trigger course auto-matching",
)
async def update_my_academic_profile(
    payload: StudentProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Academic profiling is restricted to student accounts.",
        )

    clean_student_id = payload.student_id_number.strip()
    duplicate = (
        db.query(User)
        .filter(
            User.student_id_number == clean_student_id,
            User.id != current_user.id,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Student ID '{clean_student_id}' is already registered to another student.",
        )

    current_user.student_id_number = clean_student_id
    current_user.academic_course = payload.academic_course.strip()
    current_user.academic_year = payload.academic_year.strip()
    current_user.semester = payload.semester.strip()
    current_user.year_of_study = payload.year_of_study.strip()

    db.commit()
    db.refresh(current_user)

    from app.services.enrollment import auto_enroll_student_in_matching_courses
    auto_enroll_student_in_matching_courses(current_user, db)

    return UserResponse.model_validate(current_user)


@router.patch(
    "/{user_id}/academic-profile",
    response_model=UserResponse,
    summary="Update a student's academic profile (Admin only)",
)
def update_student_academic_profile(
    user_id: int,
    payload: AdminStudentAcademicProfileUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> UserResponse:
    student = db.query(User).filter(User.id == user_id).first()
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found.",
        )
    if student.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Academic profiles can only be updated for student accounts.",
        )

    student.academic_course = payload.academic_course
    student.year_of_study = payload.year_of_study
    student.semester = payload.semester
    student.academic_year = payload.academic_year

    from app.services.enrollment import auto_enroll_student_in_matching_courses

    try:
        auto_enroll_student_in_matching_courses(student, db, commit=False)
        db.commit()
        db.refresh(student)
    except Exception:
        db.rollback()
        raise

    return UserResponse.model_validate(student)
