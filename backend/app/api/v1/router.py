"""
API v1 Router Aggregator.
Combines sub-routers into a unified v1 router.
"""

from app.api.v1.endpoints import authorized_enrollments
from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    db_test,
    auth,
    questions,
    execution,
    editor_events,
    submissions,
    university,
    users,
    certificates,
    approvals,
)

api_router = APIRouter()

# Core system endpoints
api_router.include_router(health.router)
api_router.include_router(db_test.router)

# Authentication & User Management
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(authorized_enrollments.router, prefix="/authorized-enrollments", tags=["Enrollment Authorization"])

# Question & Problem Statement Management
api_router.include_router(questions.router, prefix="/questions", tags=["Questions"])

# Code Execution & Sandboxing (Chunk 5)
api_router.include_router(execution.router, prefix="/execute", tags=["Execution"])

# Anti-Cheating & Activity Monitoring (Chunk 6)
api_router.include_router(editor_events.router, prefix="/editor-events", tags=["Editor Events"])

# Submissions, Automated Grading & Evaluation (Chunk 7)
api_router.include_router(submissions.router, prefix="/submissions", tags=["Submissions"])

# University Labs & Practical Management (Chunk 8)
api_router.include_router(university.courses_router, prefix="/courses", tags=["Courses"])
api_router.include_router(university.labs_router, prefix="/labs", tags=["Labs"])
api_router.include_router(university.practicals_router, prefix="/practicals", tags=["Practicals"])

# Cryptographic Completion Certificates (Chunk 10)
api_router.include_router(certificates.router, prefix="/certificates", tags=["Certificates"])

# Registration Approvals
api_router.include_router(approvals.router, prefix="/approvals", tags=["Registration Approvals"])



