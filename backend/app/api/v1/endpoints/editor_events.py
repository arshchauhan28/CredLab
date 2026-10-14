"""
Editor Events & Activity Telemetry Ingestion Endpoint (Chunk 6).
Accepts bounded batches of editor activity and restricted-action attempt events.
Enforces authentication and server-side user association.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.editor_event import EditorEvent
from app.models.user import User
from app.schemas.editor_event import (
    EventBatchIngestRequest,
    EventBatchIngestResponse,
)

logger = logging.getLogger("secure_coding_platform.endpoints.editor_events")

router = APIRouter()


@router.post(
    "",
    response_model=EventBatchIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest batch of editor activity events",
    description=(
        "Ingests a bounded batch of editor keystrokes, activity signals, and "
        "anti-copy/paste attempt events. Requires authentication; user ID is "
        "strictly associated from the current session token."
    ),
)
async def ingest_editor_events(
    payload: EventBatchIngestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EventBatchIngestResponse:
    """
    Ingests and persists a batch of editor activity events.

    - Authenticates via JWT (`get_current_user`).
    - Validates batch size (1 - 200 events).
    - Validates allowed event types (TYPE, DELETE, PASTE_ATTEMPT, COPY_ATTEMPT, CUT_ATTEMPT, DROP_ATTEMPT).
    - Enforces data minimization: source code and clipboard contents are strictly forbidden.
    - Associates all events with current_user.id on the server.
    """
    if not payload.events:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Event batch cannot be empty.",
        )

    try:
        db_events = [
            EditorEvent(
                user_id=current_user.id,
                question_id=item.question_id,
                event_type=item.event_type,
                event_timestamp=item.event_timestamp,
                language=item.language,
                session_id=item.session_id,
                metadata_json=item.metadata,
            )
            for item in payload.events
        ]

        db.add_all(db_events)
        db.commit()

        logger.debug(
            f"Ingested {len(db_events)} editor events for user_id={current_user.id}"
        )

        return EventBatchIngestResponse(
            accepted=len(db_events),
            status="ok",
            message=f"Successfully ingested {len(db_events)} events.",
        )

    except Exception as exc:
        db.rollback()
        logger.error(
            f"Failed to ingest editor events for user {current_user.id}: {exc}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while persisting editor activity events.",
        )
