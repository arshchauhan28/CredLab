"""
Pydantic Schemas for Cryptographic Completion Certificates.
Defines request, response, and verification schemas for tamper-evident digital completion records.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CertificateIssueRequest(BaseModel):
    """Request payload to issue a completion certificate for a practical."""
    practical_id: int = Field(..., description="ID of the completed LabPractical")


class CertificateCanonicalPayload(BaseModel):
    """
    Deterministic canonical payload structure signed by Ed25519.
    Contains all security-relevant fields identifying the achievement.
    """
    certificate_id: str = Field(..., description="Unique UUID of the certificate")
    schema_version: str = Field("1.0", description="Certificate schema specification version")
    issuer: str = Field("LabOS Sentinel", description="Authoritative issuer identity")
    algorithm: str = Field("ED25519-SHA256", description="Signature and digest algorithm identifier")
    key_id: str = Field(..., description="Signing key ID used for signature")
    student_id: int = Field(..., description="Student user ID")
    student_name: str = Field(..., description="Student display name")
    course_id: int = Field(..., description="Course ID")
    course_code: str = Field(..., description="Course code (e.g. CS201)")
    lab_id: int = Field(..., description="Lab ID")
    lab_title: str = Field(..., description="Lab title")
    practical_id: int = Field(..., description="Practical ID")
    practical_title: str = Field(..., description="Practical title")
    submission_id: int = Field(..., description="Verified passing submission ID")
    score: float = Field(..., description="Final verified score percentage")
    passing_threshold: float = Field(..., description="Practical passing threshold percentage")
    completed_at: str = Field(..., description="UTC ISO-8601 timestamp when submission was evaluated")
    issued_at: str = Field(..., description="UTC ISO-8601 timestamp when certificate was issued")


class CertificateResponse(BaseModel):
    """Full certificate response for authorized student, faculty, and administrator inspection."""
    id: str = Field(..., description="Certificate UUID")
    student_id: int
    student_name: str
    course_id: int
    course_code: str
    lab_id: Optional[int] = None
    lab_title: Optional[str] = None
    practical_id: Optional[int] = None
    practical_title: Optional[str] = None
    submission_id: Optional[int] = None
    score: Optional[float] = None
    passing_threshold: Optional[float] = None
    certificate_type: Optional[str] = "PRACTICAL"
    schema_version: str
    issuer: str
    algorithm: str
    key_id: str
    payload: Dict[str, Any]
    payload_digest: str = Field(..., description="SHA-256 digest of canonical payload (hex)")
    signature: str = Field(..., description="Ed25519 signature over canonical payload (hex)")
    status: str = Field(..., description="ACTIVE, REVOKED, or SUPERSEDED")
    completed_at: datetime
    issued_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CertificatePublicResponse(BaseModel):
    """
    Sanitized public certificate response exposing only non-sensitive verification data.
    Excludes internal database foreign keys and submission traces.
    """
    certificate_id: str
    student_name: str
    course_code: str
    course_name: Optional[str] = ""
    certificate_type: Optional[str] = "PRACTICAL"
    lab_title: Optional[str] = ""
    practical_title: Optional[str] = ""
    score: Optional[float] = 100.0
    passing_threshold: Optional[float] = 100.0
    completed_practicals_count: Optional[int] = None
    total_practicals_count: Optional[int] = None
    completed_at: str
    issued_at: str
    issuer: str
    algorithm: str
    key_id: str
    payload_digest: str
    signature: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class CertificateVerifyRequest(BaseModel):
    """
    Request payload for cryptographic certificate verification.
    Can verify by existing certificate ID or by client-supplied payload and signature.
    """
    certificate_id: Optional[str] = Field(None, description="UUID of certificate in database to verify")
    payload: Optional[Dict[str, Any]] = Field(None, description="Structured canonical payload dictionary")
    payload_digest: Optional[str] = Field(None, description="SHA-256 payload digest (hex)")
    signature: Optional[str] = Field(None, description="Ed25519 signature (hex)")
    key_id: Optional[str] = Field(None, description="Key ID used to sign payload")
    algorithm: Optional[str] = Field(None, description="Algorithm identifier (default ED25519-SHA256)")
    schema_version: Optional[str] = Field(None, description="Schema version")


class CertificateVerifyResponse(BaseModel):
    """
    Structured outcome of cryptographic certificate verification.
    Distinguishes valid state from specific failure modes.
    """
    is_valid: bool = Field(..., description="True if digest matches and Ed25519 signature is valid")
    verification_status: str = Field(
        ...,
        description="VALID | DIGEST_MISMATCH | INVALID_SIGNATURE | UNKNOWN_KEY | MALFORMED_CERTIFICATE | UNSUPPORTED_VERSION | NOT_FOUND",
    )
    message: str = Field(..., description="Human-readable verification diagnostic message")
    certificate_id: Optional[str] = None
    key_id: Optional[str] = None
    algorithm: Optional[str] = None
    verified_at: str = Field(..., description="UTC ISO-8601 timestamp when verification was executed")
    details: Optional[Dict[str, Any]] = Field(None, description="Non-sensitive certificate verification metadata")


class PublicKeyInfo(BaseModel):
    """Public key metadata safe for public export."""
    key_id: str
    public_key_hex: str
    algorithm: str = "ED25519-SHA256"
    description: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
