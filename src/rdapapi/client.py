"""Sync and async clients for the RDAP API."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Union

import httpx

from ._version import __version__
from .exceptions import (
    AuthenticationError,
    GatewayTimeoutError,
    MethodNotAllowedError,
    NotFoundError,
    NotSupportedError,
    PayloadTooLargeError,
    PlanUpgradeRequiredError,
    RateLimitError,
    RdapApiError,
    RequestFailedError,
    ServerError,
    SubscriptionRequiredError,
    TemporarilyUnavailableError,
    UpstreamError,
    ValidationError,
)
from .models import (
    AsnResponse,
    BulkDomainResponse,
    DomainResponse,
    EntityResponse,
    IpResponse,
    NameserverResponse,
    PingResponse,
    TldListResponse,
    TldResponse,
)

_DEFAULT_BASE_URL = "https://rdapapi.io/api/v1"
_DEFAULT_TIMEOUT = 30
_USER_AGENT = f"rdapapi-python/{__version__}"

_ERROR_MAP: Dict[int, type] = {
    400: ValidationError,
    401: AuthenticationError,
    403: SubscriptionRequiredError,
    404: NotFoundError,
    405: MethodNotAllowedError,
    413: PayloadTooLargeError,
    422: RequestFailedError,
    429: RateLimitError,
    502: UpstreamError,
    503: TemporarilyUnavailableError,
    504: GatewayTimeoutError,
}


def _retry_after_header(value: str) -> Optional[int]:
    """Seconds from a ``Retry-After`` header, in either form RFC 9110 allows.

    The API passes an upstream registry's own header through verbatim, so the
    HTTP-date form arrives as often as delta-seconds.
    """
    try:
        return int(value)
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0, math.ceil((when - datetime.now(timezone.utc)).total_seconds()))


def _retry_after(body: dict, response: httpx.Response) -> Optional[int]:
    """Seconds to wait before retrying, from the ``Retry-After`` header or the body.

    The header wins: it is what the limiter or the upstream actually sent.
    """
    header = response.headers.get("Retry-After")
    if header is not None:
        seconds = _retry_after_header(header)
        if seconds is not None:
            return seconds
    try:
        return int(body.get("retry_after"))
    except (TypeError, ValueError):
        return None


def _raise_for_status(response: httpx.Response) -> None:
    """Raise a typed exception for error responses."""
    if response.status_code >= 400:
        try:
            body = response.json()
        except Exception:
            # A non-JSON body means the edge answered, not the API. Treat it as a
            # transport failure: retryable when the status says so.
            body = {}

        if not isinstance(body, dict):
            body = {}

        error = body.get("error", "unknown_error")
        message = body.get("message", f"HTTP {response.status_code}")
        exc_class = _ERROR_MAP.get(response.status_code)
        if exc_class is None:
            exc_class = ServerError if response.status_code >= 500 else RdapApiError

        if exc_class is NotFoundError and error == "not_supported":
            exc_class = NotSupportedError
        elif exc_class is SubscriptionRequiredError and error == "plan_upgrade_required":
            exc_class = PlanUpgradeRequiredError

        kwargs: Dict[str, Any] = {
            "status_code": response.status_code,
            "error": error,
            "retry_after": _retry_after(body, response),
        }

        if exc_class is RequestFailedError:
            kwargs["errors"] = body.get("errors") or {}

        raise exc_class(message, **kwargs)


def _parse_bulk_response(data: dict) -> BulkDomainResponse:
    """Parse a bulk domain response, copying meta into each successful result's data."""
    for result in data.get("results", []):
        if result.get("status") == "success" and "data" in result and "meta" in result:
            result["data"]["meta"] = result["meta"]
    return BulkDomainResponse.model_validate(data)


def _domain_params(*, follow: bool, whois: bool) -> Optional[Dict[str, str]]:
    params: Dict[str, str] = {}
    if follow:
        params["follow"] = "true"
    if not whois:
        params["whois"] = "false"
    return params or None


def _bulk_body(domains: List[str], *, follow: bool, whois: bool) -> Dict[str, Any]:
    body: Dict[str, Any] = {"domains": domains}
    if follow:
        body["follow"] = True
    if not whois:
        body["whois"] = False
    return body


def _tlds_params(*, since: Optional[str], server: Optional[str]) -> Optional[Dict[str, str]]:
    params: Dict[str, str] = {}
    if since is not None:
        params["since"] = since
    if server is not None:
        params["server"] = server
    return params or None


class RdapApi:
    """Synchronous client for the RDAP API.

    Usage::

        from rdapapi import RdapApi

        api = RdapApi("your-api-key")
        domain = api.domain("google.com")
        print(domain.registrar.name)
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must be a non-empty string")
        self._client = httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "User-Agent": _USER_AGENT,
                "Accept": "application/json",
            },
            timeout=timeout,
        )

    def _request(
        self,
        path: str,
        params: Optional[Dict[str, str]] = None,
    ) -> dict:
        response = self._client.get(path, params=params)
        _raise_for_status(response)
        return response.json()

    def _post(
        self,
        path: str,
        body: Dict[str, Any],
    ) -> dict:
        response = self._client.post(path, json=body)
        _raise_for_status(response)
        return response.json()

    def _conditional_get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, str]] = None,
        if_none_match: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        headers = {"If-None-Match": if_none_match} if if_none_match else None
        response = self._client.get(path, params=params, headers=headers)
        if response.status_code == 304:
            return None
        _raise_for_status(response)
        payload = response.json()
        payload["etag"] = response.headers.get("ETag")
        return payload

    def ping(self) -> PingResponse:
        """Check that the API is reachable. Costs no quota.

        The endpoint itself answers unauthenticated callers, but this client always
        sends the key it was built with, which it requires.
        """
        data = self._request("/ping")
        return PingResponse.model_validate(data)

    def domain(self, name: str, *, follow: bool = False, whois: bool = True) -> DomainResponse:
        """Look up RDAP registration data for a domain name.

        Set ``whois=False`` to refuse the WHOIS fallback, so a TLD with no RDAP
        server raises :class:`NotSupportedError` instead of answering over port 43.
        """
        data = self._request(f"/domain/{name}", params=_domain_params(follow=follow, whois=whois))
        return DomainResponse.model_validate(data)

    def ip(self, address: str) -> IpResponse:
        """Look up RDAP registration data for an IP address.

        Accepts a plain address, which returns the most specific allocation covering
        it, or a CIDR block such as ``8.8.8.0/24``, which returns that network.
        """
        data = self._request(f"/ip/{address}")
        return IpResponse.model_validate(data)

    def asn(self, number: Union[int, str]) -> AsnResponse:
        """Look up RDAP registration data for an ASN.

        Accepts an integer (15169) or string ("AS15169" or "15169").
        """
        value = str(number).upper().removeprefix("AS")
        data = self._request(f"/asn/{value}")
        return AsnResponse.model_validate(data)

    def nameserver(self, host: str) -> NameserverResponse:
        """Look up RDAP registration data for a nameserver."""
        data = self._request(f"/nameserver/{host}")
        return NameserverResponse.model_validate(data)

    def entity(self, handle: str) -> EntityResponse:
        """Look up RDAP registration data for an entity by handle."""
        data = self._request(f"/entity/{handle}")
        return EntityResponse.model_validate(data)

    def bulk_domains(
        self,
        domains: List[str],
        *,
        follow: bool = False,
        whois: bool = True,
    ) -> BulkDomainResponse:
        """Look up multiple domains in a single request.

        Sends up to 10 domains concurrently. Requires a Pro or Business plan.
        Each domain counts as one request toward your quota. ``follow`` and
        ``whois`` apply to every domain in the request.
        """
        data = self._post("/domains/bulk", _bulk_body(domains, follow=follow, whois=whois))
        return _parse_bulk_response(data)

    def tlds(
        self,
        *,
        since: Optional[str] = None,
        server: Optional[str] = None,
        if_none_match: Optional[str] = None,
    ) -> Optional[TldListResponse]:
        """List every TLD the API can resolve, over RDAP or WHOIS.

        Does not count against the monthly quota. Returns ``None`` when an
        ``if_none_match`` tag is provided and matches the server's current
        ``ETag`` (HTTP 304). Otherwise returns a :class:`TldListResponse` whose
        ``etag`` attribute can be passed back on a later call to skip unchanged
        transfers.
        """
        params = _tlds_params(since=since, server=server)
        payload = self._conditional_get("/tlds", params=params, if_none_match=if_none_match)
        if payload is None:
            return None
        return TldListResponse.model_validate(payload)

    def tld(self, tld: str, *, if_none_match: Optional[str] = None) -> Optional[TldResponse]:
        """Return catalog metadata for a single TLD, served over RDAP or WHOIS.

        Does not count against the monthly quota. Returns ``None`` on HTTP 304.
        Raises :class:`NotFoundError` only when neither protocol covers the TLD;
        one with no RDAP server but a WHOIS one still answers.
        """
        payload = self._conditional_get(f"/tlds/{tld}", if_none_match=if_none_match)
        if payload is None:
            return None
        return TldResponse.model_validate(payload)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> RdapApi:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncRdapApi:
    """Asynchronous client for the RDAP API.

    Usage::

        from rdapapi import AsyncRdapApi

        async with AsyncRdapApi("your-api-key") as api:
            domain = await api.domain("google.com")
            print(domain.registrar.name)
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must be a non-empty string")
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "User-Agent": _USER_AGENT,
                "Accept": "application/json",
            },
            timeout=timeout,
        )

    async def _request(
        self,
        path: str,
        params: Optional[Dict[str, str]] = None,
    ) -> dict:
        response = await self._client.get(path, params=params)
        _raise_for_status(response)
        return response.json()

    async def _post(
        self,
        path: str,
        body: Dict[str, Any],
    ) -> dict:
        response = await self._client.post(path, json=body)
        _raise_for_status(response)
        return response.json()

    async def _conditional_get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, str]] = None,
        if_none_match: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        headers = {"If-None-Match": if_none_match} if if_none_match else None
        response = await self._client.get(path, params=params, headers=headers)
        if response.status_code == 304:
            return None
        _raise_for_status(response)
        payload = response.json()
        payload["etag"] = response.headers.get("ETag")
        return payload

    async def ping(self) -> PingResponse:
        """Check that the API is reachable. Costs no quota.

        The endpoint itself answers unauthenticated callers, but this client always
        sends the key it was built with, which it requires.
        """
        data = await self._request("/ping")
        return PingResponse.model_validate(data)

    async def domain(self, name: str, *, follow: bool = False, whois: bool = True) -> DomainResponse:
        """Look up RDAP registration data for a domain name.

        Set ``whois=False`` to refuse the WHOIS fallback, so a TLD with no RDAP
        server raises :class:`NotSupportedError` instead of answering over port 43.
        """
        data = await self._request(f"/domain/{name}", params=_domain_params(follow=follow, whois=whois))
        return DomainResponse.model_validate(data)

    async def ip(self, address: str) -> IpResponse:
        """Look up RDAP registration data for an IP address.

        Accepts a plain address, which returns the most specific allocation covering
        it, or a CIDR block such as ``8.8.8.0/24``, which returns that network.
        """
        data = await self._request(f"/ip/{address}")
        return IpResponse.model_validate(data)

    async def asn(self, number: Union[int, str]) -> AsnResponse:
        """Look up RDAP registration data for an ASN.

        Accepts an integer (15169) or string ("AS15169" or "15169").
        """
        value = str(number).upper().removeprefix("AS")
        data = await self._request(f"/asn/{value}")
        return AsnResponse.model_validate(data)

    async def nameserver(self, host: str) -> NameserverResponse:
        """Look up RDAP registration data for a nameserver."""
        data = await self._request(f"/nameserver/{host}")
        return NameserverResponse.model_validate(data)

    async def entity(self, handle: str) -> EntityResponse:
        """Look up RDAP registration data for an entity by handle."""
        data = await self._request(f"/entity/{handle}")
        return EntityResponse.model_validate(data)

    async def bulk_domains(
        self,
        domains: List[str],
        *,
        follow: bool = False,
        whois: bool = True,
    ) -> BulkDomainResponse:
        """Look up multiple domains in a single request.

        Sends up to 10 domains concurrently. Requires a Pro or Business plan.
        Each domain counts as one request toward your quota. ``follow`` and
        ``whois`` apply to every domain in the request.
        """
        data = await self._post("/domains/bulk", _bulk_body(domains, follow=follow, whois=whois))
        return _parse_bulk_response(data)

    async def tlds(
        self,
        *,
        since: Optional[str] = None,
        server: Optional[str] = None,
        if_none_match: Optional[str] = None,
    ) -> Optional[TldListResponse]:
        """List every TLD the API can resolve, over RDAP or WHOIS.

        Does not count against the monthly quota. Returns ``None`` when an
        ``if_none_match`` tag is provided and matches the server's current
        ``ETag`` (HTTP 304). Otherwise returns a :class:`TldListResponse` whose
        ``etag`` attribute can be passed back on a later call to skip unchanged
        transfers.
        """
        params = _tlds_params(since=since, server=server)
        payload = await self._conditional_get("/tlds", params=params, if_none_match=if_none_match)
        if payload is None:
            return None
        return TldListResponse.model_validate(payload)

    async def tld(self, tld: str, *, if_none_match: Optional[str] = None) -> Optional[TldResponse]:
        """Return catalog metadata for a single TLD, served over RDAP or WHOIS.

        Does not count against the monthly quota. Returns ``None`` on HTTP 304.
        Raises :class:`NotFoundError` only when neither protocol covers the TLD;
        one with no RDAP server but a WHOIS one still answers.
        """
        payload = await self._conditional_get(f"/tlds/{tld}", if_none_match=if_none_match)
        if payload is None:
            return None
        return TldResponse.model_validate(payload)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> AsyncRdapApi:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
