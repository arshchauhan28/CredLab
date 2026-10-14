"""Request and response schemas for administrative enrollment authorization."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.user import UserRole
from app.schemas.user import ALL_ADMIN_JOB_ROLES, validate_enrollment_number


class AuthorizedEnrollmentCreate(BaseModel):
    enrollment_number: str = Field(..., min_length=10, max_length=10)
    expected_role: UserRole
    admin_job_role: Optional[str] = Field(None, max_length=100)
    course_id: Optional[int] = Field(None, ge=1)
    is_active: bool = True

    @field_validator("enrollment_number")
    @classmethod
    def normalize_enrollment(cls, value: str) -> str:
        return validate_enrollment_number(value)

    @field_validator("admin_job_role")
    @classmethod
    def normalize_admin_job_role(cls, value: Optional[str]) -> Optional[str]:
        if value is None or not value.strip():
            return None
        normalized = value.strip().upper()
        if normalized not in ALL_ADMIN_JOB_ROLES:
            raise ValueError(f"Invalid administrative job role. Allowed values: {', '.join(sorted(ALL_ADMIN_JOB_ROLES))}.")
        return normalized

    @model_validator(mode="after")
    def require_matching_admin_job_role(self):
        if self.expected_role == UserRole.ADMIN and not self.admin_job_role:
            raise ValueError("ADMIN authorizations must specify an explicit admin_job_role.")
        if self.expected_role != UserRole.ADMIN and self.admin_job_role:
            raise ValueError("admin_job_role is only valid for ADMIN authorizations.")
        return self


class AuthorizedEnrollmentUpdate(BaseModel):
    is_active: Optional[bool] = None
    admin_job_role: Optional[str] = Field(None, max_length=100)

    @field_validator("admin_job_role")
    @classmethod
    def normalize_admin_job_role(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().upper()
        if normalized not in ALL_ADMIN_JOB_ROLES:
            raise ValueError(f"Invalid administrative job role. Allowed values: {', '.join(sorted(ALL_ADMIN_JOB_ROLES))}.")
        return normalized


class AuthorizedEnrollmentResponse(BaseModel):
    id: int
    enrollment_number: str
    expected_role: UserRole
    admin_job_role: Optional[str] = None
    is_active: bool
    course_id: Optional[int] = None
    claimed_by_user_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
