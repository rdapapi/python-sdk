"""Exception classes for the RDAP API SDK."""

from __future__ import annotations

__all__ = [
    "RdapApiError",
    "AuthenticationError",
    "SubscriptionRequiredError",
    "NotFoundError",
    "NotSupportedError",
    "ValidationError",
    "RateLimitError",
    "TemporarilyUnavailableError",
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
    """Raised when no RDAP data is found for the query (HTTP 404).

    Returned when the namespace (TLD, IP range, ASN range, nameserver TLD, entity
    handle pattern) is covered by an RDAP server but no matching record exists.
    """


class NotSupportedError(NotFoundError):
    """Raised when the query targets a namespace not covered by RDAP (HTTP 404).

    Returned when there is no RDAP server for the TLD, the IP/ASN range, or the
    entity handle pattern. Inherits from :class:`NotFoundError` so existing
    catch-all ``except NotFoundError`` blocks keep working.
    """


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


class TemporarilyUnavailableError(RdapApiError):
    """Raised when the domain data is temporarily unavailable (HTTP 503)."""

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
