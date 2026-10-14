"""
Pydantic Schemas for University Management.
Validates requests and structures responses for Courses, Labs, Practicals,
Faculty Assignments, and Course Enrollments.
"""

import enum
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# -----------------------------------------------------------------------------
# Course Schemas
# -----------------------------------------------------------------------------

class CourseCreate(BaseModel):
    # `code` is an optional subject code. Null codes are allowed and do not
    # participate in duplicate checks; supplied codes must remain unique.
    code: Optional[str] = Field(None, min_length=2, max_length=50, description="Optional subject code e.g. CS101")
    name: str = Field(..., min_length=2, max_length=255, description="Subject name")
    program: str = Field("General", min_length=2, max_length=100, description="Academic program")
    year_of_study: str = Field("1st Year", min_length=1, max_length=30, description="Year of study")
    description: Optional[str] = Field(None, description="Subject description")
    semester: str = Field(..., min_length=1, max_length=50, description="Semester number")
    academic_year: Optional[str] = Field(None, max_length=50, description="Academic session e.g. 2026-2027")
    faculty_id: Optional[int] = Field(None, gt=0, description="Faculty member assigned to the subject")
    is_active: bool = Field(True, description="Active status")


class CourseUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    program: Optional[str] = Field(None, min_length=2, max_length=100)
    year_of_study: Optional[str] = Field(None, min_length=1, max_length=30)
    description: Optional[str] = None
    semester: Optional[str] = Field(None, min_length=1, max_length=50)
    academic_year: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class CourseResponse(BaseModel):
    id: int
    code: Optional[str] = None
    name: str
    program: str = "General"
    year_of_study: str = "1st Year"
    description: Optional[str] = None
    semester: str
    academic_year: Optional[str] = None
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    lab_count: int = 0
    student_count: int = 0
    faculty_count: int = 0
    faculty_names: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Faculty Course Assignment Schemas
# -----------------------------------------------------------------------------

class FacultyAssignRequest(BaseModel):
    faculty_id: int = Field(..., description="ID of the faculty user to assign")


class FacultyAssignmentResponse(BaseModel):
    id: int
    course_id: int
    faculty_id: int
    faculty_name: Optional[str] = None
    faculty_email: Optional[str] = None
    assigned_at: datetime
    assigned_by: int

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Course Enrollment Schemas
# -----------------------------------------------------------------------------

class CourseEnrollmentRequest(BaseModel):
    student_id: int = Field(..., description="ID of the student user to enroll")
    status: Optional[str] = Field("ENROLLED", description="Enrollment status")


class CourseEnrollmentResponse(BaseModel):
    id: int
    course_id: int
    student_id: int
    student_name: Optional[str] = None
    student_email: Optional[str] = None
    enrolled_at: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Lab Schemas
# -----------------------------------------------------------------------------

class LabCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255, description="Lab title")
    description: Optional[str] = Field(None, description="Lab summary or objectives")
    instructions: Optional[str] = Field(None, description="General lab guidance / rubric")
    display_order: int = Field(0, ge=0, description="Display order within course")
    is_published: bool = Field(False, description="Whether lab is published to students")


class LabUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    instructions: Optional[str] = None
    display_order: Optional[int] = Field(None, ge=0)
    is_published: Optional[bool] = None


class LabResponse(BaseModel):
    id: int
    course_id: int
    title: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    display_order: int
    is_published: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    practical_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------------------------
# Lab Practical Schemas
# -----------------------------------------------------------------------------

class PracticalUnlockStatus(str, enum.Enum):
    LOCKED = "LOCKED"
    AVAILABLE = "AVAILABLE"
    COMPLETED = "COMPLETED"


class LabPracticalCreate(BaseModel):
    question_id: int = Field(..., description="Reference to existing coding question")
    title: Optional[str] = Field(None, max_length=255, description="Optional practical title override")
    effective_title: Optional[str] = Field(None, max_length=255, description="Optional practical title override alias")
    instructions: Optional[str] = Field(None, description="Optional practical instructions override")
    sequence_number: Optional[int] = Field(None, ge=1, description="Order position of practical within lab (1-based, auto-calculated if omitted)")
    is_required: bool = Field(True, description="Whether this practical is required")
    passing_threshold: float = Field(100.0, ge=0.0, le=100.0, description="Passing score percentage threshold (0-100)")


class LabPracticalUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    instructions: Optional[str] = None
    sequence_number: Optional[int] = Field(None, ge=1)
    is_required: Optional[bool] = None
    passing_threshold: Optional[float] = Field(None, ge=0.0, le=100.0, description="Passing score percentage threshold (0-100)")


class LabPracticalResponse(BaseModel):
    id: int
    lab_id: int
    question_id: int
    question_title: Optional[str] = None
    question_slug: Optional[str] = None
    question_difficulty: Optional[str] = None
    title: Optional[str] = None
    instructions: Optional[str] = None
    effective_title: str
    sequence_number: int
    is_required: bool
    passing_threshold: float = 100.0
    status: PracticalUnlockStatus = PracticalUnlockStatus.AVAILABLE
    is_unlocked: bool = True
    best_score: Optional[float] = None
    lock_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
