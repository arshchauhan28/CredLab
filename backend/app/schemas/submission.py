"""
Pydantic Schemas for Permanent Submissions, Automated Grading & Test Cases (Chunk 7).
Defines schemas for submission requests, submission histories, individual test results,
and authorized test case management.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.submission import SubmissionStatus
from app.services.judge0 import PLATFORM_TO_JUDGE0_LANG_ID

MAX_SOURCE_CODE_BYTES = 65536  # 64 KB limit


class SubmissionCreateRequest(BaseModel):
    """
    Candidate code submission request payload.
    Identity (user_id) is strictly extracted from server-side JWT authentication,
    never from client-supplied request bodies.
    """
    question_id: int = Field(..., description="Target question ID to evaluate against")
    practical_id: Optional[int] = Field(None, description="Target university LabPractical ID (if submitted within a lab)")
    language: str = Field(..., description="Platform language identifier slug (e.g. python, cpp, java)")
    source_code: str = Field(..., description="Submitted solution source code")

    @field_validator("source_code")
    @classmethod
    def validate_source_code(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("source_code cannot be empty or only whitespace.")
        if len(v.encode("utf-8")) > MAX_SOURCE_CODE_BYTES:
            raise ValueError(
                f"source_code exceeds the maximum allowable size of {MAX_SOURCE_CODE_BYTES} bytes."
            )
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in PLATFORM_TO_JUDGE0_LANG_ID:
            supported = ", ".join(PLATFORM_TO_JUDGE0_LANG_ID.keys())
            raise ValueError(
                f"Unsupported language '{clean}'. Supported languages are: {supported}"
            )
        return clean


class SubmissionTestResultResponse(BaseModel):
    """
    Safe test-case execution outcome returned to candidate.
    Crucial Security Rule: Hidden test inputs and expected outputs must NEVER be included.
    """
    id: int
    submission_id: int
    test_case_id: Optional[int] = None
    status: str
    passed: bool
    execution_time_ms: Optional[int] = None
    memory_kb: Optional[int] = None
    is_hidden: bool = False
    display_order: int = 0
    # Public test cases include input/expected_output/stdout; hidden cases obscure them
    input: Optional[str] = None
    expected_output: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionResponse(BaseModel):
    """
    Complete submission grading outcome returned to candidate.
    Contains overall status, score, pass/fail counts, metrics, and safe test results.
    """
    id: int
    user_id: int
    question_id: int
    practical_id: Optional[int] = None
    language: str
    source_code: Optional[str] = None
    status: SubmissionStatus
    total_test_cases: int
    passed_test_cases: int
    score: float
    execution_time_ms: Optional[int] = None
    memory_kb: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    test_results: Optional[List[SubmissionTestResultResponse]] = None

    model_config = ConfigDict(from_attributes=True)


class SubmissionListItem(BaseModel):
    """
    Paginated submission history summary item.
    Never exposes complete source code or test case inputs/outputs to prevent data leakage.
    """
    id: int
    user_id: int
    question_id: int
    practical_id: Optional[int] = None
    language: str
    status: SubmissionStatus
    total_test_cases: int
    passed_test_cases: int
    score: float
    execution_time_ms: Optional[int] = None
    memory_kb: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionListResponse(BaseModel):
    """
    Paginated submission history envelope.
    """
    items: List[SubmissionListItem]
    total: int
    page: int
    page_size: int
    pages: int

    model_config = ConfigDict(from_attributes=True)


class TestCaseCreate(BaseModel):
    """
    Schema for creating an authoritative test case (Admin only).
    """
    input: str = Field(..., description="Standard input provided to candidate solution")
    expected_output: str = Field(..., description="Expected output from correct solution")
    is_hidden: bool = Field(default=False, description="Whether test case is hidden from candidate")
    display_order: int = Field(default=0, description="Order of evaluation / display")
    weight: float = Field(default=1.0, ge=0.0, description="Score weight for this test case")

    @field_validator("input", "expected_output")
    @classmethod
    def validate_not_none(cls, v: str) -> str:
        if v is None:
            return ""
        return v


class TestCaseResponse(BaseModel):
    """
    Administrative test case response schema (Admin only).
    """
    id: int
    question_id: int
    input: str
    expected_output: str
    is_hidden: bool
    display_order: int
    weight: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
