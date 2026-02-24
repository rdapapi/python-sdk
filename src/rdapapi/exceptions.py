"""Exception classes for the RDAP API SDK."""

from __future__ import annotations

__all__ = [
    "RdapApiError",
    "AuthenticationError",
    "SubscriptionRequiredError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "UpstreamError",
]


class RdapApiError(Exception):
    """Base exception for all RDAP API errors."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error = error
        self.message = message


class AuthenticationError(RdapApiError):
    """Raised when the API key is missing or invalid (HTTP 401)."""


class SubscriptionRequiredError(RdapApiError):
    """Raised when no active subscription exists (HTTP 403)."""


class NotFoundError(RdapApiError):
    """Raised when no RDAP data is found for the query (HTTP 404)."""


class ValidationError(RdapApiError):
    """Raised when the input is invalid (HTTP 400)."""


class RateLimitError(RdapApiError):
    """Raised when rate limit or monthly quota is exceeded (HTTP 429)."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error: str | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code, error=error)
        self.retry_after = retry_after


class UpstreamError(RdapApiError):
    """Raised when the upstream RDAP server fails (HTTP 502)."""
