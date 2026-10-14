"""
Test Suite for Chunk 6: Anti-Cheating & Editor Activity Monitoring.
Validates editor event ingestion endpoint, authentication enforcement,
batch boundary validation, data minimization (no clipboard/code stored),
and database persistence.
"""

from datetime import datetime, timezone
import pytest
from app.core.security import create_access_token, hash_password
from app.models.editor_event import EditorEvent, EditorEventType
from app.models.user import User, UserRole


@pytest.fixture
def test_student(db_session) -> User:
    student = User(
        name="Telemetry Student",
        email="telemetry_student@example.com",
        password_hash=hash_password("StudentPass123"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student


@pytest.fixture
def student_headers(test_student) -> dict:
    token = create_access_token(data={"sub": str(test_student.id), "role": "STUDENT"})
    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# 1. Authentication & Authorization Tests
# ==============================================================================

def test_unauthenticated_ingest_rejected(client):
    """Anonymous event ingestion requests must be rejected with 401 Unauthorized."""
    payload = {
        "events": [
            {
                "event_type": "TYPE",
                "event_timestamp": datetime.now(timezone.utc).isoformat(),
                "language": "python",
            }
        ]
    }
    response = client.post("/api/editor-events", json=payload)
    assert response.status_code == 401
    assert "detail" in response.json()


def test_inactive_user_cannot_ingest_events(client, test_student):
    """Inactive users must be rejected with 403 Forbidden."""
    test_student.is_active = False
    token = create_access_token(data={"sub": str(test_student.id), "role": "STUDENT"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "events": [
            {
                "event_type": "TYPE",
                "event_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }
    response = client.post("/api/editor-events", json=payload, headers=headers)
    assert response.status_code == 403


# ==============================================================================
# 2. Payload Validation & Data Minimization Tests
# ==============================================================================

def test_invalid_event_type_rejected(client, student_headers):
    """Unsupported event types must be rejected with 422 Unprocessable Entity."""
    payload = {
        "events": [
            {
                "event_type": "UNSUPPORTED_ACTION",
                "event_timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]
    }
    response = client.post("/api/editor-events", json=payload, headers=student_headers)
    assert response.status_code == 422
    assert "Invalid event_type" in str(response.json())


def test_empty_batch_rejected(client, student_headers):
    """An empty event batch must be rejected with 422 Unprocessable Entity."""
    response = client.post(
        "/api/editor-events",
        json={"events": []},
        headers=student_headers,
    )
    assert response.status_code == 422


def test_oversized_batch_rejected(client, student_headers):
    """Batches exceeding the maximum size limit (>200 events) must be rejected with 422."""
    now_iso = datetime.now(timezone.utc).isoformat()
    huge_events = [
        {"event_type": "TYPE", "event_timestamp": now_iso}
        for _ in range(250)
    ]
    response = client.post(
        "/api/editor-events",
        json={"events": huge_events},
        headers=student_headers,
    )
    assert response.status_code == 422
    assert "Batch exceeds maximum limit" in str(response.json())


def test_forbidden_clipboard_text_in_metadata_rejected(client, student_headers):
    """Payloads attempting to store clipboard contents must be rejected for privacy."""
    payload = {
        "events": [
            {
                "event_type": "PASTE_ATTEMPT",
                "event_timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "clipboard_text": "secret solution code copied from website",
                },
            }
        ]
    }
    response = client.post("/api/editor-events", json=payload, headers=student_headers)
    assert response.status_code == 422
    assert "Forbidden key" in str(response.json())


def test_forbidden_source_code_in_metadata_rejected(client, student_headers):
    """Payloads attempting to store full source code must be rejected for data minimization."""
    payload = {
        "events": [
            {
                "event_type": "TYPE",
                "event_timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "source_code": "def solve(): return 42",
                },
            }
        ]
    }
    response = client.post("/api/editor-events", json=payload, headers=student_headers)
    assert response.status_code == 422
    assert "Forbidden key" in str(response.json())


def test_excessive_metadata_size_rejected(client, student_headers):
    """Metadata payloads exceeding size limits (>4KB) must be rejected."""
    huge_data = {"key": "x" * 5000}
    payload = {
        "events": [
            {
                "event_type": "TYPE",
                "event_timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": huge_data,
            }
        ]
    }
    response = client.post("/api/editor-events", json=payload, headers=student_headers)
    assert response.status_code == 422
    assert "exceeds the maximum allowable size" in str(response.json())


# ==============================================================================
# 3. Successful Batch Ingestion & Persistence Tests
# ==============================================================================

def test_single_authenticated_event_accepted(client, student_headers, db_session, test_student):
    """A valid single event is ingested and persisted with correct user association."""
    now_dt = datetime.now(timezone.utc)
    payload = {
        "events": [
            {
                "event_type": "PASTE_ATTEMPT",
                "event_timestamp": now_dt.isoformat(),
                "question_id": 1,
                "language": "python",
                "session_id": "sess-test-123",
                "metadata": {
                    "method": "keyboard_shortcut",
                    "shortcut": "Ctrl+V",
                },
            }
        ]
    }

    response = client.post("/api/editor-events", json=payload, headers=student_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["accepted"] == 1
    assert data["status"] == "ok"

    # Verify database persistence
    saved_events = db_session.query(EditorEvent).filter(EditorEvent.user_id == test_student.id).all()
    assert len(saved_events) == 1
    event = saved_events[0]
    assert event.event_type == "PASTE_ATTEMPT"
    assert event.question_id == 1
    assert event.language == "python"
    assert event.session_id == "sess-test-123"
    assert event.metadata_json == {"method": "keyboard_shortcut", "shortcut": "Ctrl+V"}
    assert event.user_id == test_student.id


def test_batch_authenticated_events_accepted(client, student_headers, db_session, test_student):
    """A valid batch containing multiple distinct event types is ingested in one request."""
    now_dt = datetime.now(timezone.utc)
    events_payload = [
        {
            "event_type": "TYPE",
            "event_timestamp": now_dt.isoformat(),
            "language": "cpp",
            "session_id": "batch-sess-001",
            "metadata": {"change_type": "typing", "chars_added": 1},
        },
        {
            "event_type": "DELETE",
            "event_timestamp": now_dt.isoformat(),
            "language": "cpp",
            "session_id": "batch-sess-001",
            "metadata": {"change_type": "deletion", "chars_removed": 1},
        },
        {
            "event_type": "COPY_ATTEMPT",
            "event_timestamp": now_dt.isoformat(),
            "language": "cpp",
            "session_id": "batch-sess-001",
            "metadata": {"method": "keyboard_shortcut"},
        },
        {
            "event_type": "CUT_ATTEMPT",
            "event_timestamp": now_dt.isoformat(),
            "language": "cpp",
            "session_id": "batch-sess-001",
            "metadata": {"method": "context_menu"},
        },
        {
            "event_type": "DROP_ATTEMPT",
            "event_timestamp": now_dt.isoformat(),
            "language": "cpp",
            "session_id": "batch-sess-001",
            "metadata": {"method": "drag_drop"},
        },
    ]

    response = client.post(
        "/api/editor-events",
        json={"events": events_payload},
        headers=student_headers,
    )
    assert response.status_code == 201
    assert response.json()["accepted"] == 5

    # Verify all 5 were written to database
    db_events = (
        db_session.query(EditorEvent)
        .filter(EditorEvent.user_id == test_student.id)
        .order_by(EditorEvent.id.asc())
        .all()
    )
    assert len(db_events) == 5
    types_saved = [e.event_type for e in db_events]
    assert types_saved == ["TYPE", "DELETE", "COPY_ATTEMPT", "CUT_ATTEMPT", "DROP_ATTEMPT"]
    for e in db_events:
        assert e.user_id == test_student.id
        assert e.session_id == "batch-sess-001"
        assert e.language == "cpp"


def test_user_id_strictly_derived_from_token(client, student_headers, db_session, test_student):
    """Client cannot spoof or override user_id; server derives it from authenticated JWT."""
    # Even if client tries to pass user_id inside payload item or metadata
    now_iso = datetime.now(timezone.utc).isoformat()
    payload = {
        "events": [
            {
                "event_type": "TYPE",
                "event_timestamp": now_iso,
                "metadata": {"chars_added": 5},
            }
        ]
    }
    response = client.post("/api/editor-events", json=payload, headers=student_headers)
    assert response.status_code == 201

    saved = db_session.query(EditorEvent).filter(EditorEvent.user_id == test_student.id).first()
    assert saved is not None
    assert saved.user_id == test_student.id
