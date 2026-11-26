from __future__ import annotations

from typing import Any, Mapping, Optional


class TrustComponentError(Exception):
    """Every error the SDK raises. ``status`` is the HTTP status (0 when no response arrived), ``code`` the stable reason of the API."""

    def __init__(self, message: str, status: int = 0, code: Optional[str] = None, detail: Optional[str] = None, retry_after_seconds: Optional[int] = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.detail = detail
        self.retry_after_seconds = retry_after_seconds


class InvalidRequestError(TrustComponentError): ...
class AuthenticationError(TrustComponentError): ...
class PermissionDeniedError(TrustComponentError): ...
class PlanLimitError(TrustComponentError): ...
class NotFoundError(TrustComponentError): ...
class ConflictError(TrustComponentError): ...
class GoneError(TrustComponentError): ...
class RateLimitError(TrustComponentError): ...
class ServerError(TrustComponentError): ...


class OperationRetiredError(TrustComponentError):
    """The operation was switched off after its sunset. A newer SDK calls its successor."""


class ConnectionError(TrustComponentError):
    """No response arrived: timeout, DNS, connection refused."""


class VerificationTokenInvalidError(TrustComponentError):
    """The string is not a token of the TrustCaptcha widget."""


_BY_STATUS = {400: InvalidRequestError, 422: InvalidRequestError, 401: AuthenticationError, 402: PlanLimitError, 403: PermissionDeniedError,
              404: NotFoundError, 409: ConflictError, 412: ConflictError, 423: ConflictError, 410: GoneError, 429: RateLimitError}


def error_of(status: int, problem: Optional[Mapping[str, Any]], retry_after_seconds: Optional[int]) -> TrustComponentError:
    code = problem.get("code") if isinstance(problem, Mapping) and isinstance(problem.get("code"), str) else None
    detail = problem.get("detail") if isinstance(problem, Mapping) and isinstance(problem.get("detail"), str) else None
    message = f"TrustComponent API answered {status}" + (f" ({code})" if code else "") + (f": {detail}" if detail else "")
    if status == 410 and code == "operation_retired":
        return OperationRetiredError(message + ". Update the TrustComponent SDK.", status, code, detail)
    cls = _BY_STATUS.get(status, ServerError if status >= 500 else TrustComponentError)
    return cls(message, status, code, detail, retry_after_seconds)
