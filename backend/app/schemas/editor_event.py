"""
Pydantic Schemas for Editor Activity & Anti-Cheating Telemetry Events (Chunk 6).
Handles event validation, batch boundary checking, and data minimization enforcement.
"""

from datetime import datetime
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.editor_event import EditorEventType

ALLOWED_EVENT_TYPES = {e.value for e in EditorEventType}
MAX_BATCH_SIZE = 200
MAX_METADATA_BYTES = 4096

FORBIDDEN_METADATA_KEYS = {
    "source_code",
    "code",
    "clipboard",
    "clipboard_content",
    "clipboard_text",
    "password",
    "token",
    "jwt",
}


class EditorEventItem(BaseModel):
    """
    Individual editor activity or restricted attempt event.
    Strictly forbids storing source code or clipboard text.
    User ID is not accepted here; it is strictly injected by the authenticated session.
    """
    event_type: str = Field(..., description="Normalized event type (TYPE, DELETE, PASTE_ATTEMPT, etc.)")
    event_timestamp: datetime = Field(..., description="Client-side event occurrence timestamp (ISO 8601)")
    question_id: Optional[int] = Field(default=None, description="Optional question context ID")
    language: Optional[str] = Field(default=None, max_length=50, description="Selected language slug")
    session_id: Optional[str] = Field(default=None, max_length=100, description="Client session identifier")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Non-sensitive telemetry metadata")

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        clean = v.strip().upper()
        if clean not in ALLOWED_EVENT_TYPES:
            allowed = ", ".join(sorted(ALLOWED_EVENT_TYPES))
            raise ValueError(f"Invalid event_type '{clean}'. Allowed types are: {allowed}")
        return clean

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v is None:
            return None

        # Data minimization enforcement: disallow sensitive fields
        for key in v.keys():
            if key.lower() in FORBIDDEN_METADATA_KEYS:
                raise ValueError(
                    f"Forbidden key '{key}' in metadata. Storing code or clipboard contents is prohibited."
                )

        # Enforce maximum metadata size
        serialized = json.dumps(v)
        if len(serialized.encode("utf-8")) > MAX_METADATA_BYTES:
            raise ValueError(
                f"Metadata payload exceeds the maximum allowable size of {MAX_METADATA_BYTES} bytes."
            )

        return v


class EventBatchIngestRequest(BaseModel):
    """
    Batch payload containing up to 200 editor events collected over a time window.
    """
    events: List[EditorEventItem] = Field(..., description="List of editor events to ingest")

    @field_validator("events")
    @classmethod
    def validate_batch_size(cls, v: List[EditorEventItem]) -> List[EditorEventItem]:
        if not v:
            raise ValueError("Event batch cannot be empty.")
        if len(v) > MAX_BATCH_SIZE:
            raise ValueError(
                f"Batch exceeds maximum limit of {MAX_BATCH_SIZE} events (received {len(v)})."
            )
        return v


class EventBatchIngestResponse(BaseModel):
    """
    Response returned to client confirming batch ingestion.
    """
    accepted: int = Field(..., description="Number of events successfully ingested")
    status: str = Field(default="ok", description="Status code ('ok')")
    message: Optional[str] = Field(default=None, description="Informational message")


class EditorEventResponse(BaseModel):
    """
    Normalized response schema representing a persisted editor event.
    """
    id: int
    user_id: int
    question_id: Optional[int] = None
    event_type: str
    event_timestamp: datetime
    language: Optional[str] = None
    session_id: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
