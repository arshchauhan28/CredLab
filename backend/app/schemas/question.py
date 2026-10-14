"""
Pydantic Schemas for Question Management.
Handles request validation and response serialization for programming questions.
"""

from datetime import datetime
import re
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.question import QuestionDifficulty, QuestionStatus


def slugify(text: str) -> str:
    """Helper to convert text into a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


class QuestionExampleCreate(BaseModel):
    input: str = Field(..., min_length=1, description="Example input data")
    output: str = Field(..., min_length=1, description="Expected output data")
    explanation: Optional[str] = Field(None, description="Explanation of why this output is expected")
    display_order: Optional[int] = Field(0, description="Order of appearance in problem description")


class QuestionExampleResponse(BaseModel):
    id: int
    question_id: int
    input: str
    output: str
    explanation: Optional[str] = None
    display_order: int

    model_config = ConfigDict(from_attributes=True)


class QuestionCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255, description="Problem title")
    slug: Optional[str] = Field(None, max_length=255, description="Unique URL slug (auto-generated if omitted)")
    description: str = Field(..., min_length=5, description="Full problem statement")
    input_format: Optional[str] = Field(None, description="Explanation of input format")
    output_format: Optional[str] = Field(None, description="Explanation of expected output format")
    constraints: Optional[str] = Field(None, description="Memory, time, or value constraints")
    difficulty: QuestionDifficulty = Field(default=QuestionDifficulty.EASY, description="Difficulty level")
    status: QuestionStatus = Field(default=QuestionStatus.DRAFT, description="Publishing status")
    allowed_languages: List[str] = Field(..., min_length=1, description="List of supported language identifiers")
    examples: Optional[List[QuestionExampleCreate]] = Field(default_factory=list, description="Public sample test cases")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Title cannot be empty or only whitespace.")
        return clean

    @field_validator("slug", mode="before")
    @classmethod
    def validate_or_generate_slug(cls, v: Optional[str], values) -> Optional[str]:
        if v and v.strip():
            return slugify(v)
        return None

    @field_validator("allowed_languages")
    @classmethod
    def validate_languages(cls, v: List[str]) -> List[str]:
        cleaned = [lang.strip().lower() for lang in v if lang and lang.strip()]
        if not cleaned:
            raise ValueError("At least one allowed programming language must be specified.")
        return list(dict.fromkeys(cleaned))  # Deduplicate preserving order


class QuestionUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    slug: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, min_length=5)
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    constraints: Optional[str] = None
    difficulty: Optional[QuestionDifficulty] = None
    status: Optional[QuestionStatus] = None
    allowed_languages: Optional[List[str]] = None
    examples: Optional[List[QuestionExampleCreate]] = None

    @field_validator("slug", mode="before")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            return slugify(v)
        return v

    @field_validator("allowed_languages")
    @classmethod
    def validate_languages(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            cleaned = [lang.strip().lower() for lang in v if lang and lang.strip()]
            if not cleaned:
                raise ValueError("At least one allowed programming language must be specified.")
            return list(dict.fromkeys(cleaned))
        return v


class QuestionStatusUpdate(BaseModel):
    status: QuestionStatus


class QuestionResponse(BaseModel):
    id: int
    title: str
    slug: str
    description: str
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    constraints: Optional[str] = None
    difficulty: QuestionDifficulty
    status: QuestionStatus
    created_by: int
    created_at: datetime
    updated_at: datetime
    allowed_languages: List[str]
    examples: List[QuestionExampleResponse]

    model_config = ConfigDict(from_attributes=True)


class QuestionListItem(BaseModel):
    id: int
    title: str
    slug: str
    description: str
    difficulty: QuestionDifficulty
    status: QuestionStatus
    allowed_languages: List[str]
    example_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
