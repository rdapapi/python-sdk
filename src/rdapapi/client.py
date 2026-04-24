"""Sync and async clients for the RDAP API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

import httpx

from ._version import __version__
from .exceptions import (
    AuthenticationError,
    NotFoundError,
    NotSupportedError,
    RateLimitError,
    RdapApiError,
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
    429: RateLimitError,
    502: UpstreamError,
    503: TemporarilyUnavailableError,
}


def _raise_for_status(response: httpx.Response) -> None:
    """Raise a typed exception for error responses."""
    if response.status_code >= 400:
        try:
            body = response.json()
        except Exception:
            body = {}

        error = body.get("error", "unknown_error")
        message = body.get("message", f"HTTP {response.status_code}")
        exc_class = _ERROR_MAP.get(response.status_code, RdapApiError)

        if exc_class is NotFoundError and error == "not_supported":
            exc_class = NotSupportedError

        kwargs: Dict[str, Any] = {
            "status_code": response.status_code,
            "error": error,
        }

        if exc_class in (RateLimitError, TemporarilyUnavailableError):
            retry_after = response.headers.get("Retry-After")
            kwargs["retry_after"] = int(retry_after) if retry_after else None

        raise exc_class(message, **kwargs)


def _parse_bulk_response(data: dict) -> BulkDomainResponse:
    """Parse a bulk domain response, merging meta into each successful result's data."""
    for result in data.get("results", []):
        if result.get("status") == "success" and "data" in result and "meta" in result:
            result["data"]["meta"] = result.pop("meta")
    return BulkDomainResponse.model_validate(data)


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

    def domain(self, name: str, *, follow: bool = False) -> DomainResponse:
        """Look up RDAP registration data for a domain name."""
        params = {"follow": "true"} if follow else None
        data = self._request(f"/domain/{name}", params=params)
        return DomainResponse.model_validate(data)

    def ip(self, address: str) -> IpResponse:
        """Look up RDAP registration data for an IP address."""
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
    ) -> BulkDomainResponse:
        """Look up multiple domains in a single request.

        Sends up to 10 domains concurrently. Requires a Pro or Business plan.
        Each domain counts as one request toward your quota.
        """
        body: Dict[str, Any] = {"domains": domains}
        if follow:
            body["follow"] = True
        data = self._post("/domains/bulk", body)
        return _parse_bulk_response(data)

    def tlds(
        self,
        *,
        since: Optional[str] = None,
        server: Optional[str] = None,
        if_none_match: Optional[str] = None,
    ) -> Optional[TldListResponse]:
        """List every TLD the API can resolve via RDAP.

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
        """Return catalog metadata for a single TLD.

        Does not count against the monthly quota. Returns ``None`` on HTTP 304.
        Raises :class:`NotFoundError` when no RDAP server is registered for the
        TLD.
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

    async def domain(self, name: str, *, follow: bool = False) -> DomainResponse:
        """Look up RDAP registration data for a domain name."""
        params = {"follow": "true"} if follow else None
        data = await self._request(f"/domain/{name}", params=params)
        return DomainResponse.model_validate(data)

    async def ip(self, address: str) -> IpResponse:
        """Look up RDAP registration data for an IP address."""
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
    ) -> BulkDomainResponse:
        """Look up multiple domains in a single request.

        Sends up to 10 domains concurrently. Requires a Pro or Business plan.
        Each domain counts as one request toward your quota.
        """
        body: Dict[str, Any] = {"domains": domains}
        if follow:
            body["follow"] = True
        data = await self._post("/domains/bulk", body)
        return _parse_bulk_response(data)

    async def tlds(
        self,
        *,
        since: Optional[str] = None,
        server: Optional[str] = None,
        if_none_match: Optional[str] = None,
    ) -> Optional[TldListResponse]:
        """List every TLD the API can resolve via RDAP.

        Does not count against the monthly quota. Returns ``None`` on HTTP 304.
        """
        params = _tlds_params(since=since, server=server)
        payload = await self._conditional_get("/tlds", params=params, if_none_match=if_none_match)
        if payload is None:
            return None
        return TldListResponse.model_validate(payload)

    async def tld(self, tld: str, *, if_none_match: Optional[str] = None) -> Optional[TldResponse]:
        """Return catalog metadata for a single TLD.

        Does not count against the monthly quota. Returns ``None`` on HTTP 304.
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
