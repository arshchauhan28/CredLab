"""
Judge0 Service & Sandboxed Code Execution Client.
Handles translation between platform language identifiers and Judge0 numeric language IDs,
submits source code and stdin to the Judge0 sandbox, and normalizes execution results.
"""

import asyncio
import base64
import logging
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse
import httpx

from app.core.config import settings

logger = logging.getLogger("secure_coding_platform.judge0")


# ==============================================================================
# Centralized Language Mapping
# ==============================================================================
# Platform slug -> Judge0 Language ID
# Strictly supported languages:
# - python: 71 (Python 3.8.1)
# - c: 50 (C GCC 9.2.0)
# - cpp: 54 (C++ GCC 9.2.0)
# - java: 62 (Java OpenJDK 13.0.1)
PLATFORM_TO_JUDGE0_LANG_ID: Dict[str, int] = {
    "python": 71,
    "c": 50,
    "cpp": 54,
    "java": 62,
}

# Historical Judge0 IDs preserved for graceful legacy submission decoding
HISTORICAL_JUDGE0_LANG_IDS: Dict[int, str] = {
    63: "javascript",
    74: "typescript",
    60: "go",
    73: "rust",
}

# Reverse mapping: Judge0 ID -> Platform slug
JUDGE0_LANG_ID_TO_PLATFORM: Dict[int, str] = {
    **HISTORICAL_JUDGE0_LANG_IDS,
    **{v: k for k, v in PLATFORM_TO_JUDGE0_LANG_ID.items()},
}


# ==============================================================================
# Custom Service Exceptions
# ==============================================================================
class Judge0Exception(Exception):
    """Base exception for Judge0 execution errors."""
    pass


class Judge0UnavailableException(Judge0Exception):
    """Raised when Judge0 is unreachable, connection refused, or service down."""
    pass


class Judge0TimeoutException(Judge0Exception):
    """Raised when communication with Judge0 exceeds the HTTP timeout threshold."""
    pass


class UnsupportedLanguageException(Judge0Exception):
    """Raised when an unmapped or invalid language identifier is supplied."""
    pass


# ==============================================================================
# Status Normalization
# ==============================================================================
def normalize_judge0_status(status_id: int, status_description: Optional[str] = None) -> Tuple[str, str]:
    """
    Normalizes raw Judge0 status codes into clean platform execution status categories.

    Judge0 Standard Status Codes:
      1: In Queue
      2: Processing
      3: Accepted
      4: Wrong Answer
      5: Time Limit Exceeded
      6: Compilation Error
      7: Runtime Error (SIGSEGV)
      8: Runtime Error (SIGXFSZ)
      9: Runtime Error (SIGFPE)
      10: Runtime Error (SIGABRT)
      11: Runtime Error (NZEC)
      12: Runtime Error (Other)
      13: Internal Error
      14: Exec Format Error
    """
    desc = status_description or "Unknown"

    # Distinguish Memory Limit Exceeded from other errors
    if desc and "memory" in desc.lower():
        return "Memory Limit Exceeded", desc

    if status_id in (1, 2):
        return "Running", desc
    if status_id == 3:
        return "Accepted", desc
    if status_id == 4:
        return "Wrong Answer", desc
    if status_id == 5:
        return "Time Limit Exceeded", desc
    if status_id == 6:
        return "Compilation Error", desc
    if (7 <= status_id <= 12) or status_id == 14:
        return "Runtime Error", desc
    if status_id == 13:
        return "Internal Error", desc

    return "Error", desc



# ==============================================================================
# Judge0 Client Service
# ==============================================================================
class Judge0Service:
    """
    Asynchronous client for interacting with the Judge0 sandboxed code execution engine.
    """

    def __init__(self):
        self.api_url = settings.JUDGE0_API_URL.rstrip("/")
        self.api_key = settings.JUDGE0_API_KEY
        self.timeout = settings.JUDGE0_TIMEOUT_SECONDS

    def _get_headers(self) -> Dict[str, str]:
        """Constructs headers with optional authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["X-Auth-Token"] = self.api_key
            # Also support RapidAPI header format if endpoint is on RapidAPI
            if "rapidapi" in self.api_url.lower():
                headers["X-RapidAPI-Key"] = self.api_key
                try:
                    headers["X-RapidAPI-Host"] = urlparse(self.api_url).netloc
                except Exception:
                    pass
        return headers

    def get_language_id(self, platform_lang: str) -> int:
        """
        Translates a platform language slug to the corresponding Judge0 language ID.
        Raises UnsupportedLanguageException if not mapped.
        """
        cleaned = platform_lang.strip().lower()
        if cleaned not in PLATFORM_TO_JUDGE0_LANG_ID:
            supported = ", ".join(PLATFORM_TO_JUDGE0_LANG_ID.keys())
            raise UnsupportedLanguageException(
                f"Unsupported language: '{platform_lang}'. Supported: {supported}"
            )
        return PLATFORM_TO_JUDGE0_LANG_ID[cleaned]

    async def _execute_mock(self, source_code: str, language: str, stdin: str) -> Dict[str, Any]:
        """
        Deterministic mock execution response for offline development and testing.
        Activated when settings.EXECUTION_MOCK_MODE is True.
        Never executes arbitrary code via unsandboxed host subprocesses.
        """
        logger.info(f"[MOCK MODE] Simulating execution for language={language}")
        await asyncio.sleep(0.01)  # Minimal async latency for test speed

        # Check for error triggers in test cases
        if "MOCK_TRIGGER: COMPILATION_ERROR" in source_code:
            return {
                "status": "Compilation Error",
                "status_id": 6,
                "status_description": "Compilation Error",
                "stdout": "",
                "stderr": "",
                "compile_output": "error: expected ';' before 'return'\n 12 |   return 0\n    |          ^",
                "time_ms": 15,
                "memory_kb": 1240,
                "time": "0.015",
                "memory": 1240,
                "exit_code": 1,
            }

        if "MOCK_TRIGGER: RUNTIME_ERROR" in source_code:
            return {
                "status": "Runtime Error",
                "status_id": 11,
                "status_description": "Runtime Error (NZEC)",
                "stdout": "",
                "stderr": "ZeroDivisionError: division by zero\n  File 'solution.py', line 7, in solve",
                "compile_output": "",
                "time_ms": 22,
                "memory_kb": 2540,
                "time": "0.022",
                "memory": 2540,
                "exit_code": 1,
            }

        if "MOCK_TRIGGER: TIMEOUT" in source_code:
            return {
                "status": "Time Limit Exceeded",
                "status_id": 5,
                "status_description": "Time Limit Exceeded",
                "stdout": "",
                "stderr": "Execution timed out (exceeded 2.0s CPU time limit)",
                "compile_output": "",
                "time_ms": 2005,
                "memory_kb": 8420,
                "time": "2.005",
                "memory": 8420,
                "exit_code": None,
            }

        if "MOCK_TRIGGER: MEMORY_LIMIT" in source_code:
            return {
                "status": "Memory Limit Exceeded",
                "status_id": 12,
                "status_description": "Memory Limit Exceeded",
                "stdout": "",
                "stderr": "Out of memory: memory limit of 128MB exceeded",
                "compile_output": "",
                "time_ms": 110,
                "memory_kb": 128000,
                "time": "0.110",
                "memory": 128000,
                "exit_code": 137,
            }

        # Keep compatibility with test_mock_mode_execution unit test and general testing
        output = f"Output for {language} solution\n"
        if stdin and stdin.strip():
            output += f"Received input:\n{stdin}\n"

        return {
            "status": "Accepted",
            "status_id": 3,
            "status_description": "Accepted",
            "stdout": output,
            "stderr": "",
            "compile_output": "",
            "time_ms": 38,
            "memory_kb": 3420,
            "time": "0.038",
            "memory": 3420,
            "exit_code": 0,
        }

    async def execute_code(
        self,
        source_code: str,
        language: str,
        stdin: str = "",
        cpu_time_limit: Optional[float] = None,
        memory_limit_kb: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Executes user code in a sandboxed Judge0 environment.

        Args:
            source_code: Raw source code string.
            language: Platform language slug (e.g. 'python', 'cpp', 'c', 'java').
            stdin: Standard input provided to the program.
            cpu_time_limit: Server-controlled CPU timeout in seconds.
            memory_limit_kb: Server-controlled memory limit in KB.

        Returns:
            Normalized dictionary containing execution results:
            {
                "status": "Accepted" | "Compilation Error" | "Runtime Error" | ...,
                "status_id": int,
                "status_description": str,
                "stdout": str,
                "stderr": str,
                "compile_output": str,
                "time_ms": int,
                "memory_kb": int,
                "time": Optional[str],
                "memory": Optional[int],
                "exit_code": Optional[int]
            }
        """
        lang_id = self.get_language_id(language)

        # Check for local deterministic mock mode
        if settings.EXECUTION_MOCK_MODE:
            return await self._execute_mock(source_code, language, stdin)

        # Enforce server-side execution boundaries (prevent frontend bypass)
        applied_cpu_limit = cpu_time_limit or settings.JUDGE0_CPU_TIME_LIMIT
        applied_memory_limit = memory_limit_kb or settings.JUDGE0_MEMORY_LIMIT_KB

        # Base64-encode source_code and stdin to prevent encoding issues (e.g. GCC curly quotes)
        encoded_source = base64.b64encode(source_code.encode("utf-8")).decode("ascii")
        encoded_stdin = base64.b64encode((stdin or "").encode("utf-8")).decode("ascii")

        payload = {
            "source_code": encoded_source,
            "language_id": lang_id,
            "stdin": encoded_stdin,
            "cpu_time_limit": applied_cpu_limit,
            "memory_limit": applied_memory_limit,
        }

        submission_url = f"{self.api_url}/submissions?base64_encoded=true&wait=true"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    submission_url,
                    json=payload,
                    headers=self._get_headers(),
                )

                if response.status_code not in (200, 201):
                    logger.error(
                        f"Judge0 returned unexpected status {response.status_code}: {response.text[:200]}"
                    )
                    raise Judge0Exception(
                        f"Judge0 execution failed with status {response.status_code}"
                    )

                data = response.json()

                # If wait=true was not supported or still in queue, poll if token is returned
                raw_status = data.get("status", {})
                status_id = raw_status.get("id", 1)
                token = data.get("token")

                if status_id in (1, 2) and token:
                    data = await self._poll_submission(client, token)

                return self._parse_judge0_result(data)

        except httpx.ConnectError as exc:
            logger.warning(f"Judge0 connection refused at {self.api_url}: {exc}")
            raise Judge0UnavailableException(
                "Unable to connect to Judge0 execution service. Ensure the sandbox is running."
            ) from exc

        except (httpx.TimeoutException, asyncio.TimeoutError) as exc:
            logger.warning(f"Judge0 request timed out after {self.timeout}s: {exc}")
            raise Judge0TimeoutException(
                f"Judge0 execution request timed out after {self.timeout} seconds."
            ) from exc

        except httpx.HTTPError as exc:
            logger.error(f"HTTP error communicating with Judge0: {exc}")
            raise Judge0Exception(f"Network error communicating with execution engine: {exc}") from exc

    async def _poll_submission(self, client: httpx.AsyncClient, token: str) -> Dict[str, Any]:
        """
        Polls for submission completion when wait=true returns a pending status.
        """
        poll_url = f"{self.api_url}/submissions/{token}?base64_encoded=true"
        max_attempts = 20
        poll_interval = 0.25

        for _ in range(max_attempts):
            await asyncio.sleep(poll_interval)
            resp = await client.get(poll_url, headers=self._get_headers())
            if resp.status_code == 200:
                data = resp.json()
                status_id = data.get("status", {}).get("id", 1)
                if status_id not in (1, 2):
                    return data
            elif resp.status_code == 429:
                await asyncio.sleep(0.5)

        raise Judge0TimeoutException("Execution timed out waiting for sandbox result.")

    @staticmethod
    def _safe_b64decode(val: Optional[str]) -> str:
        """Safely decodes base64-encoded strings with UTF-8 replacement."""
        if not val:
            return ""
        try:
            return base64.b64decode(val).decode("utf-8", errors="replace")
        except Exception:
            return str(val)

    def _parse_judge0_result(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes Judge0 response dictionary into platform-level execution result.
        """
        raw_status = data.get("status", {})
        status_id = raw_status.get("id", 13)
        status_desc = raw_status.get("description", "Unknown")

        normalized_status, full_desc = normalize_judge0_status(status_id, status_desc)

        # Base64-decode output streams
        stdout = self._safe_b64decode(data.get("stdout"))
        stderr = self._safe_b64decode(data.get("stderr"))
        compile_output = self._safe_b64decode(data.get("compile_output"))
        message = self._safe_b64decode(data.get("message"))

        # If compile failed and compile_output is present, ensure status reflects compilation error
        if compile_output and status_id != 6:
            normalized_status = "Compilation Error"
            status_id = 6

        # If runtime error occurred with system message but no stderr, attach message
        if message and not stderr and status_id != 3:
            stderr = message

        # Parse execution time (seconds -> milliseconds)
        raw_time = data.get("time")
        time_ms: Optional[int] = None
        if raw_time is not None:
            try:
                time_ms = int(round(float(raw_time) * 1000))
            except (ValueError, TypeError):
                time_ms = None

        # Parse memory (already in KB in Judge0)
        raw_memory = data.get("memory")
        memory_kb: Optional[int] = None
        if raw_memory is not None:
            try:
                memory_kb = int(raw_memory)
            except (ValueError, TypeError):
                memory_kb = None

        return {
            "status": normalized_status,
            "status_id": status_id,
            "status_description": full_desc,
            "stdout": stdout,
            "stderr": stderr,
            "compile_output": compile_output,
            "time_ms": time_ms,
            "memory_kb": memory_kb,
            "time": f"{time_ms / 1000:.3f}" if time_ms is not None else None,
            "memory": memory_kb,
            "exit_code": data.get("exit_code"),
        }


# Singleton service instance
judge0_service = Judge0Service()
