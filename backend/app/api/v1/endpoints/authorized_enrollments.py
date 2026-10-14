"""SUPER_ADMIN-only management of authorized enrollment numbers."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_super_admin
from app.core.database import get_db
from app.models.authorized_enrollment import AuthorizedEnrollment
from app.models.university import Course
from app.models.user import User, UserRole
from app.schemas.authorized_enrollment import (
    AuthorizedEnrollmentCreate,
    AuthorizedEnrollmentResponse,
    AuthorizedEnrollmentUpdate,
)

router = APIRouter()


@router.get("", response_model=List[AuthorizedEnrollmentResponse])
def list_authorized_enrollments(
    role: Optional[UserRole] = Query(None),
    include_inactive: bool = Query(True),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_super_admin),
):
    query = db.query(AuthorizedEnrollment)
    if role is not None:
        query = query.filter(AuthorizedEnrollment.expected_role == role)
    if not include_inactive:
        query = query.filter(AuthorizedEnrollment.is_active.is_(True))
    return query.order_by(AuthorizedEnrollment.created_at.desc()).limit(500).all()


@router.post(
    "",
    response_model=AuthorizedEnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_authorized_enrollment(
    payload: AuthorizedEnrollmentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_super_admin),
):
    existing = db.query(AuthorizedEnrollment).filter(
        AuthorizedEnrollment.enrollment_number == payload.enrollment_number
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An authorization record already exists for this enrollment number.",
        )

    if payload.course_id is not None and db.query(Course.id).filter(Course.id == payload.course_id).first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The selected course does not exist.")

    record = AuthorizedEnrollment(
        enrollment_number=payload.enrollment_number,
        expected_role=payload.expected_role,
        admin_job_role=payload.admin_job_role,
        course_id=payload.course_id,
        is_active=payload.is_active,
    )
    db.add(record)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(record)
    return record


@router.patch("/{authorization_id}", response_model=AuthorizedEnrollmentResponse)
def update_authorized_enrollment(
    authorization_id: int,
    payload: AuthorizedEnrollmentUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_super_admin),
):
    record = db.query(AuthorizedEnrollment).filter(
        AuthorizedEnrollment.id == authorization_id
    ).with_for_update().first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authorization record not found.")

    changes = payload.model_dump(exclude_unset=True)
    if "admin_job_role" in changes:
        if record.expected_role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only ADMIN authorization records can have an admin_job_role.",
            )
        record.admin_job_role = changes["admin_job_role"]
    if "is_active" in changes:
        record.is_active = changes["is_active"]

    db.commit()
    db.refresh(record)
    return record
