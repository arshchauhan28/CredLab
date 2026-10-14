"""
Code Execution API Endpoint (Chunk 5).
Handles running user code in the sandboxed Judge0 execution environment.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.execution import ExecuteCodeRequest, ExecuteCodeResponse
from app.services.judge0 import (
    Judge0Exception,
    Judge0TimeoutException,
    Judge0UnavailableException,
    UnsupportedLanguageException,
    judge0_service,
)

logger = logging.getLogger("secure_coding_platform.endpoints.execution")

router = APIRouter()


@router.post(
    "",
    response_model=ExecuteCodeResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute code in sandboxed environment",
    description="Submits source code with stdin to Judge0 sandbox. Requires authenticated user.",
)
async def execute_code(
    payload: ExecuteCodeRequest,
    current_user: User = Depends(get_current_user),
) -> ExecuteCodeResponse:
    """
    Executes code inside the isolated Judge0 container sandbox.

    - Authenticated via JWT token (`get_current_user`).
    - Translates platform language slug to Judge0 language ID.
    - Applies server-enforced CPU time and memory boundaries.
    - Normalizes status (Accepted, Compilation Error, Runtime Error, Time Limit Exceeded).
    - Returns stdout, stderr, compile output, runtime, and memory metrics.
    """
    logger.info(
        f"Execution request by user_id={current_user.id} for language={payload.language} "
        f"question_id={payload.question_id}"
    )

    try:
        result = await judge0_service.execute_code(
            source_code=payload.source_code,
            language=payload.language,
            stdin=payload.stdin or "",
        )
        return ExecuteCodeResponse(**result)

    except UnsupportedLanguageException as exc:
        logger.warning(f"Unsupported language requested by user {current_user.id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    except Judge0UnavailableException as exc:
        logger.error(f"Judge0 sandbox unavailable: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Code execution sandbox is currently unavailable. Please verify the execution engine is online.",
        )

    except Judge0TimeoutException as exc:
        logger.warning(f"Judge0 request timed out: {exc}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The execution request timed out waiting for the sandbox response.",
        )

    except Judge0Exception as exc:
        logger.error(f"Judge0 execution error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error communicating with sandboxed code execution engine.",
        )

    except Exception as exc:
        logger.error(f"Unexpected error during code execution: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while executing code.",
        )
