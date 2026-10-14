"""
FastAPI Dependencies for Authentication and Role-Based Access Control.
Provides reusable dependencies to extract the authenticated user and enforce permissions.
"""

from typing import List, Optional
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole

# HTTP Bearer scheme extractor
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Extracts Bearer token from the Authorization header, validates signature and expiration,
    retrieves the user from the database, and verifies the user is active.
    Raises:
        HTTP 401: If token is missing, invalid, expired, or user does not exist.
        HTTP 403: If the user account is marked inactive.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
        user_id_str: Optional[str] = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token: missing subject.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = int(user_id_str)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User belonging to this token no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    # Enforce approval status: PENDING and REJECTED accounts cannot access
    # protected APIs even if they possess a valid JWT.
    approval = getattr(user, "approval_status", "APPROVED")
    if approval == "PENDING":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Your account is pending approval. "
                "An administrator will review your registration shortly."
            ),
        )
    if approval == "REJECTED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account registration was not approved.",
        )

    return user


def require_roles(*allowed_roles: UserRole):
    """
    Dependency factory to enforce role-based access control.
    Example usage:
        @router.get("/admin-only", dependencies=[Depends(require_roles(UserRole.ADMIN))])
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have sufficient permissions to perform this operation.",
            )
        return current_user

    return role_checker


# Convenient pre-configured role dependencies
get_current_student = require_roles(UserRole.STUDENT)
get_current_faculty = require_roles(UserRole.FACULTY)
get_current_admin = require_roles(UserRole.ADMIN)
get_current_faculty_or_admin = require_roles(UserRole.FACULTY, UserRole.ADMIN)


def is_faculty_assigned_to_course(course_id: int, faculty_id: int, db: Session) -> bool:
    """Checks if a faculty member is explicitly assigned to a course."""
    from app.models.university import FacultyCourseAssignment
    return (
        db.query(FacultyCourseAssignment)
        .filter(
            FacultyCourseAssignment.course_id == course_id,
            FacultyCourseAssignment.faculty_id == faculty_id,
        )
        .first()
        is not None
    )


def is_student_enrolled_in_course(course_id: int, student_id: int, db: Session) -> bool:
    """Checks if a student is enrolled in a course."""
    from app.models.university import CourseEnrollment
    return (
        db.query(CourseEnrollment)
        .filter(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == student_id,
        )
        .first()
        is not None
    )


def verify_course_manage_permission(course, user: User, db: Session) -> None:
    """
    Verifies that the user has permission to manage a course (admin or assigned faculty).
    Raises HTTP 403 if unauthorized.
    """
    if user.role == UserRole.ADMIN:
        return
    if user.role == UserRole.FACULTY:
        if is_faculty_assigned_to_course(course.id, user.id, db):
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to manage this course without an assigned appointment.",
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to manage this course.",
    )


def verify_course_view_permission(course, user: User, db: Session) -> None:
    """
    Verifies that the user has permission to view a course.
    - Admins: can view all courses.
    - Faculty: can view courses to which they are assigned.
    - Students: can view courses in which they are enrolled.
    Raises HTTP 404 to avoid leaking resource existence if unauthorized.
    """
    if user.role == UserRole.ADMIN:
        return
    if user.role == UserRole.FACULTY:
        if is_faculty_assigned_to_course(course.id, user.id, db):
            return
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found.",
        )
    if user.role == UserRole.STUDENT:
        if is_student_enrolled_in_course(course.id, user.id, db):
            return
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found.",
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied.",
    )


def verify_lab_view_permission(lab, user: User, db: Session) -> None:
    """
    Verifies user permission to view a lab.
    Ensures parent course view permission, and hides unpublished labs from students.
    """
    verify_course_view_permission(lab.course, user, db)
    if user.role == UserRole.STUDENT and not lab.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lab not found.",
        )


def require_admin_job_roles(*allowed_job_roles: str):
    """Require an active ADMIN account with an explicitly allowed admin job role."""
    normalized = {role.strip().upper() for role in allowed_job_roles}

    async def job_role_checker(current_user: User = Depends(get_current_admin)) -> User:
        actual = (current_user.admin_job_role or "").strip().upper()
        if actual not in normalized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have sufficient administrative job-role permissions.",
            )
        return current_user

    return job_role_checker


get_current_super_admin = require_admin_job_roles("SUPER_ADMIN")
