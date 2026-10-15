"""
Pydantic Schemas for Code Execution (Chunk 5).
Validates execution requests and normalizes execution responses.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.judge0 import PLATFORM_TO_JUDGE0_LANG_ID

MAX_SOURCE_CODE_BYTES = 65536  # 64 KB limit
MAX_STDIN_BYTES = 65536        # 64 KB limit


class ExecuteCodeRequest(BaseModel):
    """
    Request payload for executing code in the Judge0 sandbox.
    Does NOT accept user_id; user identity is strictly extracted from JWT.
    """
    source_code: str = Field(..., description="The user source code to execute")
    language: str = Field(..., description="Platform language identifier slug (e.g., python, cpp, java)")
    stdin: Optional[str] = Field(default="", description="Standard input to provide to the process")
    question_id: Optional[int] = Field(default=None, description="Optional question context ID")

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

    @field_validator("stdin")
    @classmethod
    def validate_stdin(cls, v: Optional[str]) -> str:
        if v is None:
            return ""
        if len(v.encode("utf-8")) > MAX_STDIN_BYTES:
            raise ValueError(
                f"stdin exceeds the maximum allowable size of {MAX_STDIN_BYTES} bytes."
            )
        return v


class ExecuteCodeResponse(BaseModel):
    """
    Normalized execution response returned to the frontend workspace.
    Hides internal Judge0 infrastructure specifics.
    """
    status: str = Field(
        ...,
        description="Normalized category: Accepted, Compilation Error, Runtime Error, Time Limit Exceeded, etc."
    )
    status_id: Optional[int] = Field(None, description="Judge0 numeric status identifier")
    status_description: Optional[str] = Field(None, description="Detailed status message")
    stdout: Optional[str] = Field("", description="Standard output stream")
    stderr: Optional[str] = Field("", description="Standard error stream")
    compile_output: Optional[str] = Field("", description="Compiler diagnostic messages if compilation failed")
    time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    memory_kb: Optional[int] = Field(None, description="Memory consumption in kilobytes")
    time: Optional[str] = Field(None, description="Execution time in seconds (formatted string)")
    memory: Optional[int] = Field(None, description="Memory in kilobytes (UI alias)")
    exit_code: Optional[int] = Field(None, description="Process exit code")

    model_config = ConfigDict(from_attributes=True)
