"""
Registration Approval Endpoints.

Handles reviewing, approving, and rejecting pending faculty and administrator registrations.
Enforces the following rules:
- Faculty registrations can be approved/rejected by any approved administrator.
- Administrator registrations can ONLY be approved/rejected by a SUPER_ADMIN.
- Self-approval is strictly prohibited.
- Rejections require an explicit reason.
- Records all actions in the RegistrationApproval audit table.
"""

from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.registration_approval import RegistrationApproval
from app.schemas.approval import (
    RegistrationApprovalResponse,
    RejectionRequest,
)

router = APIRouter()


def _to_response(
    approval: RegistrationApproval,
    applicant: Optional[User],
    reviewer: Optional[User],
) -> RegistrationApprovalResponse:
    return RegistrationApprovalResponse(
        id=approval.id,
        applicant_id=approval.applicant_id,
        applicant_name=applicant.name if applicant else "Unknown",
        applicant_email=applicant.email if applicant else "Unknown",
        applicant_enrollment_number=applicant.enrollment_number if applicant else "Unknown",
        account_type=approval.account_type,
        admin_job_role=applicant.admin_job_role if applicant else None,
        decision=approval.decision,
        status=approval.decision,
        reviewer_id=approval.reviewer_id,
        reviewer_name=reviewer.name if reviewer else None,
        rejection_reason=approval.rejection_reason,
        requested_at=approval.requested_at,
        reviewed_at=approval.reviewed_at,
    )


@router.get(
    "",
    response_model=List[RegistrationApprovalResponse],
    summary="List registration approval requests (Admin only)",
)
def list_approvals(
    decision: Optional[str] = Query(None, description="Filter by decision: PENDING, APPROVED, REJECTED"),
    account_type: Optional[str] = Query(None, description="Filter by account type: FACULTY, ADMIN"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> List[RegistrationApprovalResponse]:
    """
    List registration approval requests with optional status and account type filtering.
    """
    query = db.query(RegistrationApproval)

    if decision:
        query = query.filter(RegistrationApproval.decision == decision.upper())
    if account_type:
        query = query.filter(RegistrationApproval.account_type == account_type.upper())

    records = query.order_by(RegistrationApproval.requested_at.desc()).all()

    # Preload users
    user_ids = set()
    for r in records:
        user_ids.add(r.applicant_id)
        if r.reviewer_id:
            user_ids.add(r.reviewer_id)

    users_by_id = {}
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        users_by_id = {u.id: u for u in users}

    return [
        _to_response(
            approval=r,
            applicant=users_by_id.get(r.applicant_id),
            reviewer=users_by_id.get(r.reviewer_id) if r.reviewer_id else None,
        )
        for r in records
    ]


@router.post(
    "/{approval_id}/approve",
    response_model=RegistrationApprovalResponse,
    summary="Approve a registration request",
)
def approve_registration(
    approval_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> RegistrationApprovalResponse:
    """
    Approve a pending faculty or administrator account registration.
    - Faculty accounts can be approved by any approved administrator.
    - Administrator accounts can ONLY be approved by a SUPER_ADMIN.
    - Self-approval is strictly forbidden.
    """
    approval = db.query(RegistrationApproval).filter(RegistrationApproval.id == approval_id).first()
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration approval request not found.",
        )

    # 1. Prevent self-approval
    if approval.applicant_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Self-approval is strictly forbidden. You cannot approve your own account.",
        )

    # 2. Check administrative authority
    if approval.account_type == "ADMIN":
        reviewer_job_role = (current_admin.admin_job_role or "").strip().upper()
        if reviewer_job_role != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only a SUPER_ADMIN can review and approve administrator account registrations.",
            )

    # 3. Fetch applicant
    applicant = db.query(User).filter(User.id == approval.applicant_id).first()
    if not applicant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Applicant user account not found.",
        )

    # 4. Activate applicant account
    applicant.approval_status = "APPROVED"
    applicant.is_active = True

    # 5. Update approval audit record
    approval.decision = "APPROVED"
    approval.reviewer_id = current_admin.id
    approval.reviewed_at = datetime.now(timezone.utc)
    approval.rejection_reason = None

    db.commit()
    db.refresh(approval)
    db.refresh(applicant)

    return _to_response(approval, applicant, current_admin)


@router.post(
    "/{approval_id}/reject",
    response_model=RegistrationApprovalResponse,
    summary="Reject a registration request",
)
def reject_registration(
    approval_id: int,
    payload: RejectionRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> RegistrationApprovalResponse:
    """
    Reject a pending faculty or administrator account registration with a reason.
    - Faculty accounts can be rejected by any approved administrator.
    - Administrator accounts can ONLY be rejected by a SUPER_ADMIN.
    - Self-rejection is strictly forbidden.
    - A rejection reason is required.
    """
    reason = (payload.reason or "").strip()
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A rejection reason is required to reject a registration.",
        )

    approval = db.query(RegistrationApproval).filter(RegistrationApproval.id == approval_id).first()
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration approval request not found.",
        )

    # 1. Prevent self-rejection
    if approval.applicant_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot reject your own account.",
        )

    # 2. Check authority
    if approval.account_type == "ADMIN":
        reviewer_job_role = (current_admin.admin_job_role or "").strip().upper()
        if reviewer_job_role != "SUPER_ADMIN":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only a SUPER_ADMIN can review and reject administrator account registrations.",
            )

    # 3. Fetch applicant
    applicant = db.query(User).filter(User.id == approval.applicant_id).first()
    if not applicant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Applicant user account not found.",
        )

    # 4. Reject applicant account
    applicant.approval_status = "REJECTED"

    # 5. Update audit record
    approval.decision = "REJECTED"
    approval.reviewer_id = current_admin.id
    approval.reviewed_at = datetime.now(timezone.utc)
    approval.rejection_reason = reason

    db.commit()
    db.refresh(approval)
    db.refresh(applicant)

    return _to_response(approval, applicant, current_admin)
