"""Exception classes for the RDAP API SDK."""

from __future__ import annotations

from typing import Dict, List

__all__ = [
    "RdapApiError",
    "AuthenticationError",
    "SubscriptionRequiredError",
    "PlanUpgradeRequiredError",
    "NotFoundError",
    "NotSupportedError",
    "ValidationError",
    "MethodNotAllowedError",
    "PayloadTooLargeError",
    "RequestFailedError",
    "RateLimitError",
    "ServerError",
    "TemporarilyUnavailableError",
    "UpstreamError",
    "GatewayTimeoutError",
]


class RdapApiError(Exception):
    """Base exception for all RDAP API errors.

    Branch on ``error``, the machine-readable code, rather than on ``message``.
    Any code can answer any endpoint.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error: str | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error = error
        self.message = message
        self.retry_after = retry_after


class AuthenticationError(RdapApiError):
    """Raised when the API key is missing or invalid (HTTP 401)."""


class SubscriptionRequiredError(RdapApiError):
    """Raised on HTTP 403, whatever the reason.

    Branch on ``error`` before telling anyone to subscribe: ``forbidden`` means
    this IP is temporarily blocked and the call is worth retrying later, while
    only ``subscription_required`` is about billing.
    """


class PlanUpgradeRequiredError(SubscriptionRequiredError):
    """Raised when the plan does not cover the endpoint (HTTP 403).

    Bulk lookups need Pro or Business. Inherits from
    :class:`SubscriptionRequiredError` so existing ``except`` blocks keep working.
    """


class NotFoundError(RdapApiError):
    """Raised when no RDAP data is found for the query (HTTP 404).

    Returned when the namespace (TLD, IP range, ASN range, nameserver TLD, entity
    handle pattern) is covered by an RDAP server but no matching record exists.
    """


class NotSupportedError(NotFoundError):
    """Raised when the query targets a namespace not covered by RDAP (HTTP 404).

    Returned when there is no RDAP server for the TLD, the IP/ASN range, or the
    entity handle pattern — or when there is a WHOIS fallback for the TLD and the
    request refused it with ``whois=False``. Inherits from :class:`NotFoundError`
    so existing catch-all ``except NotFoundError`` blocks keep working.
    """


class ValidationError(RdapApiError):
    """Raised when the input is invalid (HTTP 400)."""


class MethodNotAllowedError(RdapApiError):
    """Raised when the endpoint does not accept the HTTP method (HTTP 405)."""


class PayloadTooLargeError(RdapApiError):
    """Raised when the request body is too large (HTTP 413)."""


class RequestFailedError(RdapApiError):
    """Raised when the request body fails validation (HTTP 422).

    ``errors`` maps each rejected field to its messages, e.g.
    ``{"domains": ["The domains field must not have more than 10 items."]}``.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error: str | None = None,
        retry_after: int | None = None,
        errors: Dict[str, List[str]] | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code, error=error, retry_after=retry_after)
        self.errors = errors or {}


class RateLimitError(RdapApiError):
    """Raised when rate limit or monthly quota is exceeded (HTTP 429)."""


class ServerError(RdapApiError):
    """Raised on any server-side failure (HTTP 5xx).

    Base class for the specific 5xx errors below, so ``except ServerError`` covers
    everything worth retrying after a delay.
    """


class UpstreamError(ServerError):
    """Raised when the upstream RDAP server fails (HTTP 502)."""


class TemporarilyUnavailableError(ServerError):
    """Raised when the domain data is temporarily unavailable (HTTP 503)."""


class GatewayTimeoutError(ServerError):
    """Raised when the request did not complete in time (HTTP 504)."""
