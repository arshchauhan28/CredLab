"""
Automated Grading Pipeline & Test Case Evaluation Service (Chunk 7).
Executes candidate code submissions against authoritative backend test cases,
normalizes outputs, determines granular statuses and scores, persists test outcomes,
and sanitizes responses to strictly protect hidden test cases.
"""

import logging
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload

from app.models.question import Question
from app.models.submission import (
    Submission,
    SubmissionStatus,
    SubmissionTestResult,
    TestCase,
)
from app.schemas.submission import (
    SubmissionResponse,
    SubmissionTestResultResponse,
)
from app.services.judge0 import (
    Judge0Exception,
    Judge0TimeoutException,
    Judge0UnavailableException,
    judge0_service,
)

logger = logging.getLogger("secure_coding_platform.grading")


# ==============================================================================
# Output Comparison Policy
# ==============================================================================
def normalize_output(text: Optional[str]) -> str:
    """
    Normalizes program output for automated grading comparison:
    1. Replaces Windows CRLF (\\r\\n) and classic Mac CR (\\r) with standard Unix LF (\\n).
    2. Strips trailing whitespace (spaces, tabs) from each individual line.
    3. Strips leading and trailing newlines/blank lines from the overall output.
    4. Preserves all internal line structure and internal space separation between tokens.
    """
    if text is None:
        return ""
    # Normalize line endings
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    # Strip trailing whitespace on each line
    lines = [line.rstrip() for line in normalized.split("\n")]
    # Join and strip overall outer whitespace/newlines
    return "\n".join(lines).strip()


def compare_outputs(actual: Optional[str], expected: Optional[str]) -> bool:
    """
    Compares actual program output against expected output using the platform's
    normalized comparison policy.
    Returns True if normalized strings match exactly, False otherwise.
    """
    return normalize_output(actual) == normalize_output(expected)


# ==============================================================================
# Safe Test Result Serializer (Candidate Protection)
# ==============================================================================
def format_safe_test_result(
    result: SubmissionTestResult,
    test_case: Optional[TestCase],
) -> SubmissionTestResultResponse:
    """
    Serializes an individual test result for candidate-facing responses.
    CRITICAL SECURITY GUARDRAIL:
    Hidden test inputs and expected outputs must NEVER be returned to candidates.
    Only public sample test cases expose input, expected output, and stdout.
    """
    is_hidden = test_case.is_hidden if test_case else False
    display_order = test_case.display_order if test_case else 0

    if is_hidden:
        return SubmissionTestResultResponse(
            id=result.id,
            submission_id=result.submission_id,
            test_case_id=result.test_case_id,
            status=result.status,
            passed=result.passed,
            execution_time_ms=result.execution_time_ms,
            memory_kb=result.memory_kb,
            is_hidden=True,
            display_order=display_order,
            input=None,             # Obscured
            expected_output=None,   # Obscured
            stdout=None,            # Obscured
            stderr=result.stderr if result.status in ("COMPILATION_ERROR", "INTERNAL_ERROR") else None,
            error_message=result.error_message,
            created_at=result.created_at,
        )
    else:
        return SubmissionTestResultResponse(
            id=result.id,
            submission_id=result.submission_id,
            test_case_id=result.test_case_id,
            status=result.status,
            passed=result.passed,
            execution_time_ms=result.execution_time_ms,
            memory_kb=result.memory_kb,
            is_hidden=False,
            display_order=display_order,
            input=test_case.input if test_case else None,
            expected_output=test_case.expected_output if test_case else None,
            stdout=result.stdout,
            stderr=result.stderr,
            error_message=result.error_message,
            created_at=result.created_at,
        )


def build_safe_submission_response(
    submission: Submission,
    include_source: bool = True,
) -> SubmissionResponse:
    """
    Constructs a candidate-safe SubmissionResponse containing overall metrics
    and sanitized individual test results.
    """
    safe_results: List[SubmissionTestResultResponse] = []
    if submission.test_results:
        for res in submission.test_results:
            safe_results.append(format_safe_test_result(res, res.test_case))

    return SubmissionResponse(
        id=submission.id,
        user_id=submission.user_id,
        question_id=submission.question_id,
        practical_id=submission.practical_id,
        language=submission.language,
        source_code=submission.source_code if include_source else None,
        status=submission.status,
        total_test_cases=submission.total_test_cases,
        passed_test_cases=submission.passed_test_cases,
        score=submission.score,
        execution_time_ms=submission.execution_time_ms,
        memory_kb=submission.memory_kb,
        error_message=submission.error_message,
        created_at=submission.created_at,
        updated_at=submission.updated_at,
        test_results=safe_results,
    )


# ==============================================================================
# Automated Grading Service
# ==============================================================================
class GradingService:
    """
    Coordinates end-to-end execution and automated evaluation of candidate submissions.
    """

    @staticmethod
    def map_judge0_to_submission_status(
        judge0_result: dict,
        expected_output: str,
    ) -> Tuple[str, bool, Optional[str]]:
        """
        Maps raw Judge0 execution outcome to platform status category,
        pass/fail boolean, and sanitized error diagnostic.
        """
        status_id = judge0_result.get("status_id", 13)
        stdout = judge0_result.get("stdout") or ""
        stderr = judge0_result.get("stderr") or ""
        compile_output = judge0_result.get("compile_output") or ""

        # Compilation Error (Status 6)
        if status_id == 6 or compile_output:
            return "COMPILATION_ERROR", False, compile_output or "Compilation failed."

        # Time Limit Exceeded (Status 5)
        if status_id == 5:
            return "TIME_LIMIT_EXCEEDED", False, "Time limit exceeded."

        # Runtime Error (Statuses 7-12, 14)
        if (7 <= status_id <= 12) or status_id == 14:
            return "RUNTIME_ERROR", False, stderr or "Process terminated with runtime error."

        # Internal Error (Status 13)
        if status_id == 13:
            return "INTERNAL_ERROR", False, "Execution engine encountered an internal error."

        # Accepted from execution sandbox (Status 3) -> verify against expected output
        if status_id == 3:
            matches = compare_outputs(stdout, expected_output)
            if matches:
                return "ACCEPTED", True, None
            else:
                return "WRONG_ANSWER", False, None

        # Fallback for unknown status
        return "WRONG_ANSWER", False, stderr or "Output did not match expected result."

    async def evaluate_submission(
        self,
        db: Session,
        submission: Submission,
    ) -> Submission:
        """
        Orchestrates automated evaluation of a submission record:
        1. Selects authoritative test cases.
        2. Executes solution against each test case via Judge0.
        3. Compares outputs and logs results.
        4. Calculates score and final status.
        5. Persists records within database transactions.
        """
        # Fetch question and its authoritative test cases
        question = (
            db.query(Question)
            .options(joinedload(Question.test_cases))
            .filter(Question.id == submission.question_id)
            .first()
        )

        if not question or not question.test_cases:
            submission.status = SubmissionStatus.INTERNAL_ERROR
            submission.error_message = (
                "Question does not have any configured grading test cases. "
                "Please contact an administrator to configure test cases before submitting."
            )
            submission.total_test_cases = 0
            submission.passed_test_cases = 0
            submission.score = 0.0
            db.commit()
            db.refresh(submission)
            return submission

        # Update status to RUNNING
        submission.status = SubmissionStatus.RUNNING
        db.commit()

        # Sort test cases by display_order, then id
        test_cases = sorted(question.test_cases, key=lambda tc: (tc.display_order, tc.id))
        total_cases = len(test_cases)
        passed_cases = 0
        total_weight = sum(tc.weight for tc in test_cases)
        passed_weight = 0.0

        max_execution_time_ms: Optional[int] = None
        max_memory_kb: Optional[int] = None

        first_failure_status: Optional[str] = None
        compilation_error_msg: Optional[str] = None
        runtime_error_msg: Optional[str] = None

        test_results: List[SubmissionTestResult] = []

        try:
            for tc in test_cases:
                # If a compilation error was already detected, skip subsequent executions
                if compilation_error_msg:
                    res_record = SubmissionTestResult(
                        submission_id=submission.id,
                        test_case_id=tc.id,
                        status="COMPILATION_ERROR",
                        passed=False,
                        execution_time_ms=0,
                        memory_kb=0,
                        stdout="",
                        stderr="",
                        error_message="Compilation failed.",
                    )
                    db.add(res_record)
                    test_results.append(res_record)
                    continue

                try:
                    judge0_resp = await judge0_service.execute_code(
                        source_code=submission.source_code,
                        language=submission.language,
                        stdin=tc.input or "",
                    )
                    
                    status_name, passed, err_msg = self.map_judge0_to_submission_status(
                        judge0_resp,
                        tc.expected_output,
                    )

                    time_ms = judge0_resp.get("time_ms")
                    mem_kb = judge0_resp.get("memory_kb")
                    stdout_str = judge0_resp.get("stdout") or ""
                    stderr_str = judge0_resp.get("stderr") or ""

                    if time_ms is not None:
                        max_execution_time_ms = (
                            max(max_execution_time_ms, time_ms)
                            if max_execution_time_ms is not None
                            else time_ms
                        )
                    if mem_kb is not None:
                        max_memory_kb = (
                            max(max_memory_kb, mem_kb)
                            if max_memory_kb is not None
                            else mem_kb
                        )

                    if passed:
                        passed_cases += 1
                        passed_weight += tc.weight
                    else:
                        if first_failure_status is None:
                            first_failure_status = status_name
                        if status_name == "COMPILATION_ERROR" and not compilation_error_msg:
                            compilation_error_msg = err_msg or "Compilation error occurred."
                        elif status_name == "RUNTIME_ERROR" and not runtime_error_msg:
                            runtime_error_msg = err_msg

                    res_record = SubmissionTestResult(
                        submission_id=submission.id,
                        test_case_id=tc.id,
                        status=status_name,
                        passed=passed,
                        execution_time_ms=time_ms,
                        memory_kb=mem_kb,
                        stdout=stdout_str,
                        stderr=stderr_str,
                        error_message=err_msg,
                    )
                    db.add(res_record)
                    test_results.append(res_record)

                except Judge0TimeoutException as exc:
                    logger.warning(f"Timeout evaluating submission {submission.id} on test case {tc.id}: {exc}")
                    if first_failure_status is None:
                        first_failure_status = "TIME_LIMIT_EXCEEDED"
                    res_record = SubmissionTestResult(
                        submission_id=submission.id,
                        test_case_id=tc.id,
                        status="TIME_LIMIT_EXCEEDED",
                        passed=False,
                        execution_time_ms=int(judge0_service.timeout * 1000),
                        memory_kb=None,
                        stdout="",
                        stderr="Execution timed out.",
                        error_message="Time limit exceeded during evaluation.",
                    )
                    db.add(res_record)
                    test_results.append(res_record)

                except Judge0UnavailableException as exc:
                    logger.error(f"Judge0 unavailable while grading submission {submission.id}: {exc}")
                    first_failure_status = "INTERNAL_ERROR"
                    res_record = SubmissionTestResult(
                        submission_id=submission.id,
                        test_case_id=tc.id,
                        status="INTERNAL_ERROR",
                        passed=False,
                        execution_time_ms=None,
                        memory_kb=None,
                        stdout="",
                        stderr="",
                        error_message="Execution engine service is unavailable.",
                    )
                    db.add(res_record)
                    test_results.append(res_record)
                    # Don't keep hammering unavailable sandbox
                    break

                except Judge0Exception as exc:
                    logger.error(f"Judge0 error grading submission {submission.id}: {exc}")
                    if first_failure_status is None:
                        first_failure_status = "INTERNAL_ERROR"
                    res_record = SubmissionTestResult(
                        submission_id=submission.id,
                        test_case_id=tc.id,
                        status="INTERNAL_ERROR",
                        passed=False,
                        execution_time_ms=None,
                        memory_kb=None,
                        stdout="",
                        stderr=str(exc),
                        error_message="Sandbox execution failure.",
                    )
                    db.add(res_record)
                    test_results.append(res_record)

            # Calculate score: percentage of total weight (or count)
            if total_weight > 0:
                calculated_score = round((passed_weight / total_weight) * 100.0, 2)
            else:
                calculated_score = round((passed_cases / total_cases) * 100.0, 2) if total_cases > 0 else 0.0

            # Determine aggregate submission status
            if passed_cases == total_cases and total_cases > 0:
                aggregate_status = SubmissionStatus.ACCEPTED
            elif compilation_error_msg:
                aggregate_status = SubmissionStatus.COMPILATION_ERROR
            elif first_failure_status == "TIME_LIMIT_EXCEEDED":
                aggregate_status = SubmissionStatus.TIME_LIMIT_EXCEEDED
            elif first_failure_status == "RUNTIME_ERROR":
                aggregate_status = SubmissionStatus.RUNTIME_ERROR
            elif first_failure_status == "INTERNAL_ERROR":
                aggregate_status = SubmissionStatus.INTERNAL_ERROR
            else:
                aggregate_status = SubmissionStatus.WRONG_ANSWER

            # Update submission attributes
            submission.status = aggregate_status
            submission.total_test_cases = total_cases
            submission.passed_test_cases = passed_cases
            submission.score = calculated_score
            submission.execution_time_ms = max_execution_time_ms
            submission.memory_kb = max_memory_kb
            submission.error_message = compilation_error_msg or runtime_error_msg

            db.commit()
            db.refresh(submission)
            logger.info(
                f"Submission {submission.id} graded: status={submission.status} "
                f"score={submission.score}% ({passed_cases}/{total_cases} passed)"
            )
            return submission

        except Exception as exc:
            db.rollback()
            logger.error(f"Unexpected error evaluating submission {submission.id}: {exc}", exc_info=True)
            submission.status = SubmissionStatus.INTERNAL_ERROR
            submission.error_message = "An unexpected error occurred during grading."
            db.commit()
            db.refresh(submission)
            return submission


# Singleton grading service instance
grading_service = GradingService()
