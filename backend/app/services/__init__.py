"""
Services Package.
Provides external service integrations and background workers.
"""

from app.services.judge0 import (
    Judge0Service,
    judge0_service,
    Judge0Exception,
    Judge0UnavailableException,
    Judge0TimeoutException,
    UnsupportedLanguageException,
    PLATFORM_TO_JUDGE0_LANG_ID,
    JUDGE0_LANG_ID_TO_PLATFORM,
)

from app.services.grading import (
    GradingService,
    grading_service,
    normalize_output,
    compare_outputs,
    build_safe_submission_response,
    format_safe_test_result,
)

from app.services.certificate import (
    CertificateService,
    certificate_service,
    serialize_canonical_payload,
    compute_payload_digest,
    format_utc_timestamp,
)

from app.services.enrollment import (
    auto_enroll_student_in_matching_courses,
    auto_enroll_students_in_new_course,
)

__all__ = [
    "Judge0Service",
    "judge0_service",
    "Judge0Exception",
    "Judge0UnavailableException",
    "Judge0TimeoutException",
    "UnsupportedLanguageException",
    "PLATFORM_TO_JUDGE0_LANG_ID",
    "JUDGE0_LANG_ID_TO_PLATFORM",
    "GradingService",
    "grading_service",
    "normalize_output",
    "compare_outputs",
    "build_safe_submission_response",
    "format_safe_test_result",
    "CertificateService",
    "certificate_service",
    "serialize_canonical_payload",
    "compute_payload_digest",
    "format_utc_timestamp",
    "auto_enroll_student_in_matching_courses",
    "auto_enroll_students_in_new_course",
]

