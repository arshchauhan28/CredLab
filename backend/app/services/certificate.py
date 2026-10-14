"""
Cryptographic Completion Certificate & Ed25519 Digital Signature Service.
Implements:
1. Canonical JSON payload construction and deterministic UTF-8 serialization.
2. SHA-256 payload digest calculation.
3. Ed25519 digital signature generation and verification using cryptography library.
4. Secure key management (dev-key isolation, rotation support, safe error handling).
5. Comprehensive certificate verification distinguishing specific failure modes.
6. Authoritative university practical completion verification and idempotent certificate issuance.
"""

import hashlib
import json
import logging
import os
import stat
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, Union

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.certificate import CertificateSigningKey, CompletionCertificate
from app.models.submission import Submission, SubmissionStatus
from app.models.university import (
    Course,
    CourseEnrollment,
    Lab,
    LabPractical,
)
from app.models.user import User
from app.schemas.certificate import (
    CertificateCanonicalPayload,
    CertificateResponse,
    CertificateVerifyResponse,
)

logger = logging.getLogger("secure_coding_platform.certificates")

SUPPORTED_SCHEMA_VERSIONS = {"1.0"}
SUPPORTED_ALGORITHMS = {"ED25519-SHA256"}


def format_utc_timestamp(dt: Union[datetime, str]) -> str:
    """
    Formats a datetime object to an unambiguous ISO 8601 UTC string with 'Z' suffix.
    E.g.: 2026-10-11T12:00:00Z
    """
    if isinstance(dt, str):
        # Normalize existing ISO string
        clean_str = dt.replace("+00:00", "Z")
        if not clean_str.endswith("Z"):
            try:
                parsed = datetime.fromisoformat(clean_str)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                else:
                    parsed = parsed.astimezone(timezone.utc)
                return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                return clean_str
        return clean_str

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def serialize_canonical_payload(payload: Dict[str, Any]) -> bytes:
    """
    Produces deterministic UTF-8 canonical bytes for a certificate payload.
    Rules:
    - Excludes non-security fields (digest, signature) to prevent circular signing.
    - Deterministic field ordering (alphabetically sorted keys).
    - Compact separators (no trailing spaces: separators=(',', ':')).
    - Explicit float representation rounded to 2 decimal places.
    - Stable ISO 8601 UTC timestamp representation with 'Z' suffix.
    """
    # Exclude digest and signature if present
    filtered = {
        k: v
        for k, v in payload.items()
        if k not in ("payload_digest", "signature", "status")
    }

    # Normalize numeric scores and timestamps
    normalized: Dict[str, Any] = {}
    for k, v in filtered.items():
        if k in ("score", "passing_threshold") and v is not None:
            normalized[k] = round(float(v), 2)
        elif k in ("completed_at", "issued_at") and v is not None:
            normalized[k] = format_utc_timestamp(v)
        else:
            normalized[k] = v

    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def compute_payload_digest(canonical_bytes: bytes) -> str:
    """
    Computes standard SHA-256 hexadecimal digest from canonical payload bytes.
    Returns 64 lowercase hexadecimal characters.
    """
    return hashlib.sha256(canonical_bytes).hexdigest()


class CertificateService:
    """
    Centralized service for completion certificate signing, verification, and lifecycle management.
    """

    def __init__(self):
        self._dev_key: Optional[ed25519.Ed25519PrivateKey] = None

    def get_active_signing_key(self) -> Tuple[str, ed25519.Ed25519PrivateKey]:
        """
        Retrieves the active Ed25519 private key and associated key ID.
        Fails safely in production if configuration is missing or invalid.
        Never reveals private key material in logs or exceptions.
        """
        key_id = settings.CERTIFICATE_KEY_ID

        # 1. Direct hex private key from environment / secrets manager
        if settings.CERTIFICATE_PRIVATE_KEY_HEX:
            hex_val = settings.CERTIFICATE_PRIVATE_KEY_HEX.strip()
            try:
                raw_bytes = bytes.fromhex(hex_val)
                if len(raw_bytes) == 32:
                    return key_id, ed25519.Ed25519PrivateKey.from_private_bytes(raw_bytes)
                else:
                    raise ValueError("Private key must be exactly 32 bytes (64 hex characters).")
            except Exception as e:
                logger.error(f"Failed to load CERTIFICATE_PRIVATE_KEY_HEX: invalid hex key format.")
                raise RuntimeError("Invalid certificate private key configuration.") from None

        # 2. File-based private key path
        key_path = settings.CERTIFICATE_PRIVATE_KEY_PATH
        if key_path:
            full_path = key_path if os.path.isabs(key_path) else os.path.abspath(key_path)
            if os.path.isfile(full_path):
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                    raw_bytes = bytes.fromhex(content)
                    return key_id, ed25519.Ed25519PrivateKey.from_private_bytes(raw_bytes)
                except Exception:
                    logger.error("Failed to load private key from file path.")
                    raise RuntimeError("Invalid certificate private key file.") from None

        # 3. Development / test ephemeral key generation (strictly disabled in production)
        is_production = settings.ENVIRONMENT.lower() == "production"
        if is_production:
            logger.critical("Certificate private signing key is missing in production environment!")
            raise RuntimeError("Certificate signing key is not configured for production.")

        # In development/test: generate or load dev key if permitted
        if self._dev_key is not None:
            return key_id, self._dev_key

        dev_keys_dir = os.path.abspath(".keys")
        dev_key_file = os.path.join(dev_keys_dir, "dev_ed25519_private.key")

        if os.path.isfile(dev_key_file):
            try:
                with open(dev_key_file, "r", encoding="utf-8") as f:
                    hex_key = f.read().strip()
                self._dev_key = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(hex_key))
                return key_id, self._dev_key
            except Exception:
                pass

        if settings.CERTIFICATE_DEV_KEY_AUTOGEN:
            os.makedirs(dev_keys_dir, exist_ok=True)
            new_key = ed25519.Ed25519PrivateKey.generate()
            private_bytes = new_key.private_bytes_raw()
            with open(dev_key_file, "w", encoding="utf-8") as f:
                f.write(private_bytes.hex())
            try:
                os.chmod(dev_key_file, stat.S_IRUSR | stat.S_IWUSR)
            except Exception:
                pass
            self._dev_key = new_key
            return key_id, self._dev_key

        # Ephemeral in-memory key for tests / dev
        self._dev_key = ed25519.Ed25519PrivateKey.generate()
        return key_id, self._dev_key

    def get_public_key_hex(self, key_id: str, db: Optional[Session] = None) -> Optional[str]:
        """
        Looks up the 32-byte Ed25519 public key (hex) for a given key ID.
        Searches:
        1. Configured static trusted public keys in settings (for rotation).
        2. Database public key registry table.
        3. Active signing key (if key_id matches current active key).
        """
        # 1. Configured dictionary in settings
        trusted_map = settings.CERTIFICATE_TRUSTED_PUBLIC_KEYS
        if isinstance(trusted_map, dict) and key_id in trusted_map:
            return trusted_map[key_id].strip().lower()

        # 2. Database registry
        if db is not None:
            db_key = (
                db.query(CertificateSigningKey)
                .filter(CertificateSigningKey.key_id == key_id, CertificateSigningKey.is_active == True)
                .first()
            )
            if db_key and db_key.public_key_hex:
                return db_key.public_key_hex.strip().lower()

        # 3. Active key fallback
        try:
            active_key_id, active_priv_key = self.get_active_signing_key()
            if active_key_id == key_id:
                pub_hex = active_priv_key.public_key().public_bytes_raw().hex()
                # Persist to DB registry if db is provided
                if db is not None:
                    self.register_public_key(
                        db=db,
                        key_id=key_id,
                        public_key_hex=pub_hex,
                        description="Auto-registered active signing key",
                    )
                return pub_hex
        except Exception:
            pass

        return None

    def register_public_key(
        self,
        db: Session,
        key_id: str,
        public_key_hex: str,
        description: Optional[str] = None,
        is_active: bool = True,
    ) -> CertificateSigningKey:
        """
        Registers or updates a trusted public key in the database registry.
        Never stores private key material.
        """
        existing = (
            db.query(CertificateSigningKey)
            .filter(CertificateSigningKey.key_id == key_id)
            .first()
        )
        if existing:
            existing.public_key_hex = public_key_hex.strip().lower()
            existing.description = description
            existing.is_active = is_active
            db.commit()
            db.refresh(existing)
            return existing

        new_key = CertificateSigningKey(
            key_id=key_id,
            public_key_hex=public_key_hex.strip().lower(),
            algorithm="ED25519-SHA256",
            description=description,
            is_active=is_active,
        )
        db.add(new_key)
        db.commit()
        db.refresh(new_key)
        return new_key

    def verify_certificate(
        self,
        certificate_data: Union[CompletionCertificate, Dict[str, Any]],
        db: Optional[Session] = None,
    ) -> CertificateVerifyResponse:
        """
        Performs complete 7-step cryptographic verification:
        1. Validates certificate schema version and required fields.
        2. Reconstructs canonical payload.
        3. Recomputes SHA-256 digest over canonical payload bytes.
        4. Compares computed digest with stored digest.
        5. Looks up trusted public key matching key_id.
        6. Verifies Ed25519 signature over canonical payload bytes.
        7. Returns structured verification outcome distinguishing exact failure mode.
        """
        verified_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Extract fields from model or dictionary
        if isinstance(certificate_data, CompletionCertificate):
            cert_id = certificate_data.id
            schema_version = certificate_data.schema_version
            key_id = certificate_data.key_id
            algorithm = certificate_data.algorithm
            stored_digest = certificate_data.payload_digest
            signature_hex = certificate_data.signature
            payload = certificate_data.payload
        elif isinstance(certificate_data, dict):
            cert_id = certificate_data.get("id") or certificate_data.get("certificate_id")
            payload = certificate_data.get("payload")
            schema_version = certificate_data.get("schema_version")
            if not schema_version and isinstance(payload, dict):
                schema_version = payload.get("schema_version")
            key_id = certificate_data.get("key_id") or (payload.get("key_id") if isinstance(payload, dict) else None)
            algorithm = certificate_data.get("algorithm") or (payload.get("algorithm") if isinstance(payload, dict) else "ED25519-SHA256")
            stored_digest = certificate_data.get("payload_digest")
            signature_hex = certificate_data.get("signature")

            # If payload is not separately nested, extract payload fields directly
            if not payload and isinstance(certificate_data, dict):
                payload = {
                    k: v
                    for k, v in certificate_data.items()
                    if k not in ("payload_digest", "signature", "status", "id")
                }
                if cert_id and "certificate_id" not in payload:
                    payload["certificate_id"] = cert_id
        else:
            return CertificateVerifyResponse(
                is_valid=False,
                verification_status="MALFORMED_CERTIFICATE",
                message="Certificate input is not a valid certificate object or dictionary.",
                verified_at=verified_at,
            )

        # Step 1: Validate Schema Version (if explicitly specified as an unsupported version)
        if schema_version is not None and str(schema_version) not in SUPPORTED_SCHEMA_VERSIONS:
            return CertificateVerifyResponse(
                is_valid=False,
                verification_status="UNSUPPORTED_VERSION",
                message=f"Unsupported certificate schema version: '{schema_version}'.",
                certificate_id=cert_id,
                key_id=key_id,
                algorithm=algorithm,
                verified_at=verified_at,
            )

        # Step 2: Validate Required Fields
        required_fields = [
            "certificate_id",
            "student_id",
            "practical_id",
            "submission_id",
            "score",
            "passing_threshold",
            "completed_at",
            "issued_at",
            "issuer",
            "key_id",
        ]
        if not isinstance(payload, dict):
            return CertificateVerifyResponse(
                is_valid=False,
                verification_status="MALFORMED_CERTIFICATE",
                message="Certificate payload is missing or not a structured dictionary.",
                certificate_id=cert_id,
                key_id=key_id,
                algorithm=algorithm,
                verified_at=verified_at,
            )

        # Check required fields and required schema_version
        missing = [f for f in required_fields if f not in payload or payload[f] is None]
        if missing or not stored_digest or not signature_hex or not key_id or not schema_version:
            return CertificateVerifyResponse(
                is_valid=False,
                verification_status="MALFORMED_CERTIFICATE",
                message=f"Certificate is missing required security fields: {', '.join(missing or ['digest/signature/schema_version'])}.",
                certificate_id=cert_id,
                key_id=key_id,
                algorithm=algorithm,
                verified_at=verified_at,
            )

        # Step 3 & 4: Reconstruct Canonical Payload and Recompute SHA-256 Digest
        try:
            canonical_bytes = serialize_canonical_payload(payload)
            computed_digest = compute_payload_digest(canonical_bytes)
        except Exception as e:
            return CertificateVerifyResponse(
                is_valid=False,
                verification_status="MALFORMED_CERTIFICATE",
                message=f"Could not reconstruct canonical payload: {str(e)}",
                certificate_id=cert_id,
                key_id=key_id,
                algorithm=algorithm,
                verified_at=verified_at,
            )

        # Step 5: Compare Stored Digest with Recomputed Digest
        if computed_digest.lower() != stored_digest.lower():
            return CertificateVerifyResponse(
                is_valid=False,
                verification_status="DIGEST_MISMATCH",
                message="SHA-256 digest mismatch. The certificate payload has been tampered with or modified.",
                certificate_id=cert_id,
                key_id=key_id,
                algorithm=algorithm,
                verified_at=verified_at,
                details={
                    "stored_digest": stored_digest,
                    "computed_digest": computed_digest,
                },
            )

        # Step 6: Lookup Trusted Public Key for Key ID
        public_key_hex = self.get_public_key_hex(key_id, db=db)
        if not public_key_hex:
            return CertificateVerifyResponse(
                is_valid=False,
                verification_status="UNKNOWN_KEY",
                message=f"Signing key ID '{key_id}' is unknown or not in trusted public key registry.",
                certificate_id=cert_id,
                key_id=key_id,
                algorithm=algorithm,
                verified_at=verified_at,
            )

        # Step 7: Verify Ed25519 Digital Signature
        try:
            pub_bytes = bytes.fromhex(public_key_hex)
            if len(pub_bytes) != 32:
                return CertificateVerifyResponse(
                    is_valid=False,
                    verification_status="UNKNOWN_KEY",
                    message="Invalid trusted public key length.",
                    certificate_id=cert_id,
                    key_id=key_id,
                    algorithm=algorithm,
                    verified_at=verified_at,
                )

            public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
            sig_bytes = bytes.fromhex(signature_hex)
            if len(sig_bytes) != 64:
                return CertificateVerifyResponse(
                    is_valid=False,
                    verification_status="INVALID_SIGNATURE",
                    message="Invalid signature length (must be 64 bytes / 128 hex chars).",
                    certificate_id=cert_id,
                    key_id=key_id,
                    algorithm=algorithm,
                    verified_at=verified_at,
                )

            # Cryptographic signature verification over canonical bytes
            public_key.verify(sig_bytes, canonical_bytes)

        except (InvalidSignature, ValueError) as e:
            return CertificateVerifyResponse(
                is_valid=False,
                verification_status="INVALID_SIGNATURE",
                message="Ed25519 digital signature verification failed. The signature does not correspond to the payload or public key.",
                certificate_id=cert_id,
                key_id=key_id,
                algorithm=algorithm,
                verified_at=verified_at,
            )
        except Exception as e:
            return CertificateVerifyResponse(
                is_valid=False,
                verification_status="INVALID_SIGNATURE",
                message="Cryptographic verification encountered an error.",
                certificate_id=cert_id,
                key_id=key_id,
                algorithm=algorithm,
                verified_at=verified_at,
            )

        # Step 8: Success - Valid Certificate
        return CertificateVerifyResponse(
            is_valid=True,
            verification_status="VALID",
            message="Certificate is cryptographically valid and signed by authoritative issuer.",
            certificate_id=cert_id,
            key_id=key_id,
            algorithm=algorithm,
            verified_at=verified_at,
            details={
                "issuer": payload.get("issuer"),
                "student_name": payload.get("student_name"),
                "course_code": payload.get("course_code"),
                "practical_title": payload.get("practical_title"),
                "score": payload.get("score"),
                "passing_threshold": payload.get("passing_threshold"),
                "completed_at": payload.get("completed_at"),
                "issued_at": payload.get("issued_at"),
            },
        )

    def issue_certificate_for_practical(
        self,
        db: Session,
        student: User,
        practical_id: int,
    ) -> CompletionCertificate:
        """
        Validates academic eligibility and issues a signed completion certificate.
        Eligibility checks:
        1. Student is authenticated and active.
        2. Practical exists and is linked to Lab and Course.
        3. Student is currently enrolled in the Course.
        4. Practical is completed under Chunk 9 sequential unlocking rules.
        5. A verified passing submission owned by this student exists for this practical.
        6. Idempotency: Returns existing active certificate if already issued.
        """
        # 1. Look up practical
        practical = db.query(LabPractical).filter(LabPractical.id == practical_id).first()
        if not practical:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Practical not found.",
            )

        lab = practical.lab
        if not lab:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent laboratory not found.",
            )

        course = lab.course
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent course not found.",
            )

        # 2. Check student enrollment in the course
        enrollment = (
            db.query(CourseEnrollment)
            .filter(
                CourseEnrollment.course_id == course.id,
                CourseEnrollment.student_id == student.id,
                CourseEnrollment.status == "ENROLLED",
            )
            .first()
        )
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not enrolled in the course associated with this practical.",
            )

        # 3. Idempotency check: Return existing active certificate if already issued
        existing_cert = (
            db.query(CompletionCertificate)
            .filter(
                CompletionCertificate.student_id == student.id,
                CompletionCertificate.practical_id == practical.id,
                CompletionCertificate.status == "ACTIVE",
            )
            .first()
        )
        if existing_cert:
            return existing_cert

        # 4. Check sequential unlocking rules from Chunk 9
        preceding_required = (
            db.query(LabPractical)
            .filter(
                LabPractical.lab_id == lab.id,
                LabPractical.is_required == True,
                (LabPractical.sequence_number < practical.sequence_number)
                | (
                    (LabPractical.sequence_number == practical.sequence_number)
                    & (LabPractical.id < practical.id)
                ),
            )
            .order_by(LabPractical.sequence_number.asc(), LabPractical.id.asc())
            .all()
        )

        for prec in preceding_required:
            prec_pass = (
                db.query(Submission)
                .filter(
                    Submission.user_id == student.id,
                    Submission.practical_id == prec.id,
                    Submission.status.notin_([
                        SubmissionStatus.PENDING,
                        SubmissionStatus.RUNNING,
                        SubmissionStatus.COMPILATION_ERROR,
                        SubmissionStatus.RUNTIME_ERROR,
                        SubmissionStatus.TIME_LIMIT_EXCEEDED,
                        SubmissionStatus.INTERNAL_ERROR,
                    ]),
                    Submission.score >= prec.passing_threshold,
                )
                .first()
            )
            if not prec_pass:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Practical sequence #{practical.sequence_number} is locked. "
                        f"Preceding required practical sequence #{prec.sequence_number} has not been completed."
                    ),
                )

        # 5. Look up student's passing submission for this practical
        # Submissions must be linked to practical_id, belong to student, and meet passing threshold
        passing_submission = (
            db.query(Submission)
            .filter(
                Submission.user_id == student.id,
                Submission.practical_id == practical.id,
                Submission.status.notin_([
                    SubmissionStatus.PENDING,
                    SubmissionStatus.RUNNING,
                    SubmissionStatus.COMPILATION_ERROR,
                    SubmissionStatus.RUNTIME_ERROR,
                    SubmissionStatus.TIME_LIMIT_EXCEEDED,
                    SubmissionStatus.INTERNAL_ERROR,
                ]),
                Submission.score >= practical.passing_threshold,
            )
            .order_by(Submission.score.desc(), Submission.created_at.desc())
            .first()
        )

        if not passing_submission:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Practical completion requirement not met: no verified submission "
                    f"achieved the passing threshold of {practical.passing_threshold}%."
                ),
            )

        # 6. Retrieve active signing key
        key_id, private_key = self.get_active_signing_key()
        pub_key_hex = private_key.public_key().public_bytes_raw().hex()

        # Ensure public key is registered in database
        self.register_public_key(
            db=db,
            key_id=key_id,
            public_key_hex=pub_key_hex,
            description="Authoritative signing key",
        )

        # 7. Construct canonical payload
        cert_uuid = str(uuid.uuid4())
        issued_at_dt = datetime.now(timezone.utc)
        completed_at_dt = passing_submission.created_at or issued_at_dt

        effective_practical_title = (
            practical.title
            if practical.title and practical.title.strip()
            else (practical.question.title if practical.question else "Practical")
        )

        payload_dict = {
            "certificate_id": cert_uuid,
            "schema_version": settings.CERTIFICATE_SCHEMA_VERSION,
            "issuer": settings.CERTIFICATE_ISSUER_NAME,
            "algorithm": "ED25519-SHA256",
            "key_id": key_id,
            "student_id": student.id,
            "student_name": student.name,
            "course_id": course.id,
            "course_code": course.code or course.name,
            "lab_id": lab.id,
            "lab_title": lab.title,
            "practical_id": practical.id,
            "practical_title": effective_practical_title,
            "submission_id": passing_submission.id,
            "score": round(float(passing_submission.score), 2),
            "passing_threshold": round(float(practical.passing_threshold), 2),
            "completed_at": format_utc_timestamp(completed_at_dt),
            "issued_at": format_utc_timestamp(issued_at_dt),
        }

        # 8. Deterministic serialization, SHA-256 digest, and Ed25519 signing
        canonical_bytes = serialize_canonical_payload(payload_dict)
        digest_hex = compute_payload_digest(canonical_bytes)
        signature_bytes = private_key.sign(canonical_bytes)
        signature_hex = signature_bytes.hex()

        # 9. Create and persist CompletionCertificate record
        cert = CompletionCertificate(
            id=cert_uuid,
            student_id=student.id,
            practical_id=practical.id,
            submission_id=passing_submission.id,
            schema_version=settings.CERTIFICATE_SCHEMA_VERSION,
            issuer=settings.CERTIFICATE_ISSUER_NAME,
            algorithm="ED25519-SHA256",
            key_id=key_id,
            payload=payload_dict,
            payload_digest=digest_hex,
            signature=signature_hex,
            status="ACTIVE",
            completed_at=completed_at_dt,
            issued_at=issued_at_dt,
        )

        db.add(cert)
        try:
            db.commit()
            db.refresh(cert)
        except Exception as e:
            db.rollback()
            # Handle potential concurrent race condition:
            concurrent_cert = (
                db.query(CompletionCertificate)
                .filter(
                    CompletionCertificate.student_id == student.id,
                    CompletionCertificate.practical_id == practical.id,
                    CompletionCertificate.status == "ACTIVE",
                )
                .first()
            )
            if concurrent_cert:
                return concurrent_cert
            logger.error(f"Failed to persist completion certificate: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate certificate due to a database error.",
            )

        logger.info(
            f"Successfully issued certificate {cert.id} for student {student.id} "
            f"on practical {practical.id} with key {key_id}."
        )
        return cert


    def issue_subject_certificate(
        self,
        db: Session,
        student: User,
        course: Course,
    ) -> CompletionCertificate:
        """
        Validates academic completion across all required practicals in a course
        and issues a digitally signed subject-level completion certificate (Part 11).
        """
        # 1. Verify student enrollment
        enrollment = (
            db.query(CourseEnrollment)
            .filter(
                CourseEnrollment.course_id == course.id,
                CourseEnrollment.student_id == student.id,
                CourseEnrollment.status == "ENROLLED",
            )
            .first()
        )
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Student is not enrolled in this course.",
            )

        # 2. Check for existing active subject certificate (idempotent)
        existing = (
            db.query(CompletionCertificate)
            .filter(
                CompletionCertificate.student_id == student.id,
                CompletionCertificate.course_id == course.id,
                CompletionCertificate.certificate_type == "SUBJECT",
                CompletionCertificate.status == "ACTIVE",
            )
            .first()
        )
        if existing:
            return existing

        # 3. Verify that all required practicals in the course have passing submissions
        lab_ids = [l.id for l in course.labs]
        if not lab_ids:
            raise HTTPException(status_code=400, detail="This course has no practical laboratories.")

        required_practicals = (
            db.query(LabPractical)
            .filter(
                LabPractical.lab_id.in_(lab_ids),
                LabPractical.is_required.is_(True),
            )
            .all()
        )
        if not required_practicals:
            raise HTTPException(status_code=400, detail="This course has no required practicals.")

        for req in required_practicals:
            passing = (
                db.query(Submission)
                .filter(
                    Submission.user_id == student.id,
                    Submission.practical_id == req.id,
                    Submission.status == SubmissionStatus.ACCEPTED,
                    Submission.score >= req.passing_threshold,
                )
                .first()
            )
            if not passing:
                prac_name = getattr(req, "effective_title", None) or getattr(req, "title", None) or (req.question.title if getattr(req, "question", None) else str(req.id))
                raise HTTPException(
                    status_code=400,
                    detail=f"Ineligible: Required practical '{prac_name}' has not been passed.",
                )

        # 4. Sign and issue
        key_id, private_key = self.get_active_signing_key()
        pub_key_hex = private_key.public_key().public_bytes_raw().hex()
        self.register_public_key(
            db=db,
            key_id=key_id,
            public_key_hex=pub_key_hex,
            description="Authoritative signing key",
        )

        cert_uuid = str(uuid.uuid4())
        issued_at_dt = datetime.now(timezone.utc)

        payload_dict = {
            "certificate_id": cert_uuid,
            "schema_version": settings.CERTIFICATE_SCHEMA_VERSION,
            "issuer": settings.CERTIFICATE_ISSUER_NAME,
            "algorithm": "ED25519-SHA256",
            "key_id": key_id,
            "student_id": student.id,
            "student_name": student.name,
            "course_id": course.id,
            "course_code": course.code or course.name,
            "course_name": course.name,
            "certificate_type": "SUBJECT",
            "completed_practicals_count": len(required_practicals),
            "completed_at": format_utc_timestamp(issued_at_dt),
            "issued_at": format_utc_timestamp(issued_at_dt),
        }

        canonical_bytes = serialize_canonical_payload(payload_dict)
        digest_hex = compute_payload_digest(canonical_bytes)
        signature_bytes = private_key.sign(canonical_bytes)
        signature_hex = signature_bytes.hex()

        cert = CompletionCertificate(
            id=cert_uuid,
            student_id=student.id,
            course_id=course.id,
            certificate_type="SUBJECT",
            schema_version=settings.CERTIFICATE_SCHEMA_VERSION,
            issuer=settings.CERTIFICATE_ISSUER_NAME,
            algorithm="ED25519-SHA256",
            key_id=key_id,
            payload=payload_dict,
            payload_digest=digest_hex,
            signature=signature_hex,
            status="ACTIVE",
            completed_at=issued_at_dt,
            issued_at=issued_at_dt,
        )

        db.add(cert)
        try:
            db.commit()
            db.refresh(cert)
        except Exception:
            db.rollback()
            concurrent_cert = (
                db.query(CompletionCertificate)
                .filter(
                    CompletionCertificate.student_id == student.id,
                    CompletionCertificate.course_id == course.id,
                    CompletionCertificate.certificate_type == "SUBJECT",
                    CompletionCertificate.status == "ACTIVE",
                )
                .first()
            )
            if concurrent_cert:
                return concurrent_cert
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate subject certificate.",
            )

        return cert


# Global singleton instance of CertificateService
certificate_service = CertificateService()
