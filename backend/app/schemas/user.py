"""
Pydantic Schemas for User Management and Authentication.

Validates registration, enrollment-number login, academic profiles,
and safe user responses.
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

from app.models.user import UserRole


ENROLLMENT_NUMBER_PATTERN = re.compile(r"^[A-Z]{3}[0-9]{7}$")

# The six administrative designations available for public registration.
# SUPER_ADMIN is intentionally excluded — it must be provisioned out-of-band.
ADMIN_JOB_ROLES = {
    "HEAD_OF_DEPARTMENT",
    "DEAN_ACADEMICS",
    "DEAN",
    "DEPUTY_DEAN",
    "SENIOR_FACULTY",
    "ADMINISTRATIVE_MEMBER",
    "UNIVERSITY_ADMIN",
    "LAB_ADMIN",
}

ALL_ADMIN_JOB_ROLES = ADMIN_JOB_ROLES | {
    "SUPER_ADMIN",
}

ACADEMIC_PROGRAM_OPTIONS = (
    "B.Tech (CSE)",
    "B.Tech (AI & ML)",
    "B.Tech (AI & DS)",
    "M.Tech",
    "BCA",
    "MCA",
    "Diploma",
)


def validate_enrollment_number(value: str) -> str:
    """Normalize and validate an enrollment number."""

    cleaned = value.strip().upper()

    if not ENROLLMENT_NUMBER_PATTERN.fullmatch(cleaned):
        raise ValueError(
            "Enrollment number must contain three letters followed "
            "by exactly seven digits, for example MUR2502214 or EMP2500045."
        )

    return cleaned


def validate_role_prefix(enrollment_number: str, role: UserRole) -> None:
    """Validate the enrollment-number prefix for the requested role."""

    if role == UserRole.STUDENT:
        if not enrollment_number.startswith("MUR"):
            raise ValueError(
                "Student enrollment numbers must start with MUR."
            )

    elif role in {UserRole.FACULTY, UserRole.ADMIN}:
        if not enrollment_number.startswith("EMP"):
            raise ValueError(
                "Faculty and admin enrollment numbers must start with EMP."
            )


class UserRegisterRequest(BaseModel):
    """Student registration request."""

    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    enrollment_number: str = Field(..., min_length=10, max_length=10)
    academic_course: str = Field(..., min_length=1, max_length=100)
    year_of_study: str = Field("1st Year", min_length=1, max_length=30)
    semester: str = Field("Semester 1", min_length=1, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()

        if len(cleaned) < 2:
            raise ValueError("Name must be at least 2 characters long.")

        return cleaned

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("enrollment_number")
    @classmethod
    def normalize_enrollment_number(cls, value: str) -> str:
        cleaned = validate_enrollment_number(value)
        validate_role_prefix(cleaned, UserRole.STUDENT)
        return cleaned

    @field_validator("academic_course")
    @classmethod
    def clean_academic_course(cls, value: str) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("Academic course cannot be empty.")

        return cleaned

    @field_validator("year_of_study")
    @classmethod
    def validate_year_of_study(cls, value: str) -> str:
        valid_years = {"1st Year", "2nd Year", "3rd Year", "4th Year"}
        cleaned = value.strip()
        if cleaned not in valid_years:
            raise ValueError(
                f"Year of study must be one of: {', '.join(sorted(valid_years))}."
            )
        return cleaned

    @field_validator("semester")
    @classmethod
    def validate_semester(cls, value: str) -> str:
        valid_semesters = {f"Semester {i}" for i in range(1, 9)}
        cleaned = value.strip()
        if cleaned not in valid_semesters:
            raise ValueError(
                "Semester must be between Semester 1 and Semester 8."
            )
        return cleaned

    @model_validator(mode="after")
    def validate_year_semester_combination(self) -> "UserRegisterRequest":
        """Validate that the semester is appropriate for the year of study."""
        year_to_semesters: dict[str, set[str]] = {
            "1st Year": {"Semester 1", "Semester 2"},
            "2nd Year": {"Semester 3", "Semester 4"},
            "3rd Year": {"Semester 5", "Semester 6"},
            "4th Year": {"Semester 7", "Semester 8"},
        }
        allowed = year_to_semesters.get(self.year_of_study, set())
        if self.semester not in allowed:
            raise ValueError(
                f"Semester '{self.semester}' is not valid for '{self.year_of_study}'. "
                f"Expected one of: {', '.join(sorted(allowed))}."
            )
        return self


class FacultyRegisterRequest(BaseModel):
    """Faculty registration request."""

    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    enrollment_number: str = Field(..., min_length=10, max_length=10)
    teaching_subjects: list[str] = Field(
        ...,
        min_length=1,
        max_length=20,
    )
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()

        if len(cleaned) < 2:
            raise ValueError("Name must be at least 2 characters long.")

        return cleaned

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("enrollment_number")
    @classmethod
    def normalize_enrollment_number(cls, value: str) -> str:
        cleaned = validate_enrollment_number(value)
        validate_role_prefix(cleaned, UserRole.FACULTY)
        return cleaned

    @field_validator("teaching_subjects")
    @classmethod
    def validate_teaching_subjects(
        cls,
        values: list[str],
    ) -> list[str]:
        cleaned_values = list(
            dict.fromkeys(
                subject.strip()
                for subject in values
                if subject.strip()
            )
        )

        if not cleaned_values:
            raise ValueError("Select at least one teaching subject.")

        if len(cleaned_values) > 20:
            raise ValueError("You cannot select more than 20 subjects.")

        return cleaned_values


class AdminRegisterRequest(BaseModel):
    """Restricted administrator registration request."""

    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    enrollment_number: str = Field(..., min_length=10, max_length=10)
    admin_job_role: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()

        if len(cleaned) < 2:
            raise ValueError("Name must be at least 2 characters long.")

        return cleaned

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("enrollment_number")
    @classmethod
    def normalize_enrollment_number(cls, value: str) -> str:
        cleaned = validate_enrollment_number(value)
        validate_role_prefix(cleaned, UserRole.ADMIN)
        return cleaned

    @field_validator("admin_job_role")
    @classmethod
    def validate_admin_job_role(cls, value: str) -> str:
        cleaned = value.strip().upper()

        if cleaned not in ALL_ADMIN_JOB_ROLES:
            raise ValueError(
                "Invalid administrative role. Choose one of: "
                f"{', '.join(sorted(ALL_ADMIN_JOB_ROLES))}."
            )

        return cleaned


class UserLoginRequest(BaseModel):
    """Login using enrollment number and password."""

    enrollment_number: str = Field(
        ...,
        min_length=10,
        max_length=10,
    )
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("enrollment_number")
    @classmethod
    def normalize_enrollment_number(cls, value: str) -> str:
        return validate_enrollment_number(value)


class UserResponse(BaseModel):
    """Safe public user information."""

    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool

    enrollment_number: Optional[str] = None
    admin_job_role: Optional[str] = None

    student_id_number: Optional[str] = None
    academic_course: Optional[str] = None
    academic_year: Optional[str] = None
    semester: Optional[str] = None
    year_of_study: Optional[str] = None

    profile_completed: bool = True
    approval_status: Optional[str] = "APPROVED"

    assigned_courses: Optional[list[str]] = None
    enrolled_courses: Optional[list[str]] = None

    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StudentProfileUpdateRequest(BaseModel):
    """Request to update a student's academic profile."""

    student_id_number: str = Field(
        ...,
        min_length=1,
        max_length=50,
    )
    academic_course: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )
    academic_year: str = Field(
        ...,
        min_length=1,
        max_length=50,
    )
    semester: str = Field(
        ...,
        min_length=1,
        max_length=50,
    )
    year_of_study: str = Field("1st Year", min_length=1, max_length=30)

    @field_validator(
        "student_id_number",
        "academic_course",
        "academic_year",
        "semester",
        "year_of_study",
    )
    @classmethod
    def clean_strings(cls, value: str) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("Field cannot be empty or only spaces.")

        return cleaned


class AdminStudentAcademicProfileUpdateRequest(BaseModel):
    """Academic fields administrators may update without changing account identity."""

    academic_course: str = Field(..., min_length=1, max_length=100)
    year_of_study: str = Field(..., min_length=1, max_length=30)
    semester: str = Field(..., min_length=1, max_length=50)
    academic_year: str = Field(..., min_length=9, max_length=9)

    @field_validator("academic_course", "year_of_study", "semester", "academic_year")
    @classmethod
    def clean_required_fields(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty or only spaces.")
        return cleaned

    @field_validator("academic_course")
    @classmethod
    def validate_program(cls, value: str) -> str:
        if value not in ACADEMIC_PROGRAM_OPTIONS:
            raise ValueError(
                "Choose a supported program: " + ", ".join(ACADEMIC_PROGRAM_OPTIONS)
            )
        return value

    @field_validator("year_of_study")
    @classmethod
    def validate_year_of_study(cls, value: str) -> str:
        if value not in {f"{year}{suffix} Year" for year, suffix in (
            (1, "st"), (2, "nd"), (3, "rd"), (4, "th"), (5, "th")
        )}:
            raise ValueError("Year of study must be between 1st Year and 5th Year.")
        return value

    @field_validator("semester")
    @classmethod
    def validate_semester(cls, value: str) -> str:
        if value not in {f"Semester {number}" for number in range(1, 11)}:
            raise ValueError("Semester must be between Semester 1 and Semester 10.")
        return value

    @field_validator("academic_year")
    @classmethod
    def validate_academic_session(cls, value: str) -> str:
        match = re.fullmatch(r"([0-9]{4})-([0-9]{4})", value)
        if not match or int(match.group(2)) != int(match.group(1)) + 1:
            raise ValueError("Academic session must use consecutive years, for example 2026-2027.")
        return value


class TokenResponse(BaseModel):
    """JWT authentication response."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenPayload(BaseModel):
    """Decoded JWT token claims."""

    sub: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[int] = None