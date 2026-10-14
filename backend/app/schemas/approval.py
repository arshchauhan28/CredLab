from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ApprovalActionRequest(BaseModel):
    pass


class RejectionRequest(BaseModel):
    reason: str = Field(..., min_length=1, description="Reason for rejection")


class RegistrationApprovalResponse(BaseModel):
    id: int
    applicant_id: int
    applicant_name: str
    applicant_email: str
    applicant_enrollment_number: str
    account_type: str
    admin_job_role: Optional[str] = None
    decision: str
    status: Optional[str] = None
    reviewer_id: Optional[int] = None
    reviewer_name: Optional[str] = None
    rejection_reason: Optional[str] = None
    requested_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
