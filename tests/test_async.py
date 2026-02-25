"""Tests for the asynchronous RDAP API client."""

import httpx
import pytest
import respx

from rdapapi import AsyncRdapApi, AuthenticationError, NotFoundError, RateLimitError, SubscriptionRequiredError
from rdapapi.models import BulkDomainResponse

BASE_URL = "https://rdapapi.io/api/v1"

DOMAIN_RESPONSE = {
    "domain": "google.com",
    "unicode_name": None,
    "handle": "2138514_DOMAIN_COM-VRSN",
    "status": ["client delete prohibited"],
    "registrar": {"name": "MarkMonitor Inc.", "iana_id": "292", "abuse_email": None, "abuse_phone": None, "url": None},
    "dates": {"registered": "1997-09-15T04:00:00Z", "expires": "2028-09-14T04:00:00Z", "updated": None},
    "nameservers": ["ns1.google.com"],
    "dnssec": False,
    "entities": {},
    "meta": {
        "rdap_server": "https://rdap.verisign.com/com/v1/",
        "raw_rdap_url": "https://rdap.verisign.com/com/v1/domain/google.com",
        "cached": False,
        "cache_expires": "2026-02-24T15:30:00Z",
    },
}

ASN_RESPONSE = {
    "handle": "AS15169",
    "name": "GOOGLE",
    "type": None,
    "start_autnum": 15169,
    "end_autnum": 15169,
    "status": ["active"],
    "dates": {"registered": "2000-03-30T00:00:00-05:00", "expires": None, "updated": None},
    "entities": {},
    "remarks": [],
    "port43": "whois.arin.net",
    "meta": {
        "rdap_server": "https://rdap.arin.net/registry/",
        "raw_rdap_url": "https://rdap.arin.net/registry/autnum/15169",
        "cached": False,
        "cache_expires": "2026-02-24T15:30:00Z",
    },
}


@pytest.mark.asyncio
@respx.mock
async def test_async_domain_lookup():
    respx.get(f"{BASE_URL}/domain/google.com").mock(return_value=httpx.Response(200, json=DOMAIN_RESPONSE))

    async with AsyncRdapApi("test-key", base_url=BASE_URL) as api:
        result = await api.domain("google.com")

    assert result.domain == "google.com"
    assert result.registrar.name == "MarkMonitor Inc."


@pytest.mark.asyncio
@respx.mock
async def test_async_domain_with_follow():
    route = respx.get(f"{BASE_URL}/domain/google.com", params={"follow": "true"}).mock(
        return_value=httpx.Response(200, json=DOMAIN_RESPONSE)
    )

    async with AsyncRdapApi("test-key", base_url=BASE_URL) as api:
        await api.domain("google.com", follow=True)

    assert route.called


@pytest.mark.asyncio
@respx.mock
async def test_async_asn_lookup():
    respx.get(f"{BASE_URL}/asn/15169").mock(return_value=httpx.Response(200, json=ASN_RESPONSE))

    async with AsyncRdapApi("test-key", base_url=BASE_URL) as api:
        result = await api.asn("AS15169")

    assert result.handle == "AS15169"
    assert result.start_autnum == 15169


@pytest.mark.asyncio
@respx.mock
async def test_async_authentication_error():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(401, json={"error": "unauthenticated", "message": "Invalid token."})
    )

    async with AsyncRdapApi("bad-key", base_url=BASE_URL) as api:
        with pytest.raises(AuthenticationError):
            await api.domain("test.com")


@pytest.mark.asyncio
@respx.mock
async def test_async_not_found_error():
    respx.get(f"{BASE_URL}/domain/nope.example").mock(
        return_value=httpx.Response(404, json={"error": "not_found", "message": "Not found."})
    )

    async with AsyncRdapApi("test-key", base_url=BASE_URL) as api:
        with pytest.raises(NotFoundError):
            await api.domain("nope.example")


@pytest.mark.asyncio
@respx.mock
async def test_async_rate_limit_error():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(
            429,
            json={"error": "rate_limit_exceeded", "message": "Rate limit exceeded."},
            headers={"Retry-After": "30"},
        )
    )

    async with AsyncRdapApi("test-key", base_url=BASE_URL) as api:
        with pytest.raises(RateLimitError) as exc_info:
            await api.domain("test.com")

    assert exc_info.value.retry_after == 30


# === Async Bulk Domain Lookups ===

BULK_RESPONSE = {
    "results": [
        {
            "domain": "google.com",
            "status": "success",
            "data": {
                "domain": "google.com",
                "unicode_name": None,
                "handle": "2138514_DOMAIN_COM-VRSN",
                "status": ["client delete prohibited"],
                "registrar": {
                    "name": "MarkMonitor Inc.",
                    "iana_id": "292",
                    "abuse_email": None,
                    "abuse_phone": None,
                    "url": None,
                },
                "dates": {"registered": "1997-09-15T04:00:00Z", "expires": "2028-09-14T04:00:00Z", "updated": None},
                "nameservers": ["ns1.google.com"],
                "dnssec": False,
                "entities": {},
            },
            "meta": {
                "rdap_server": "https://rdap.verisign.com/com/v1/",
                "raw_rdap_url": "https://rdap.verisign.com/com/v1/domain/google.com",
                "cached": False,
                "cache_expires": "2026-02-25T15:30:00Z",
            },
        },
    ],
    "summary": {"total": 1, "successful": 1, "failed": 0},
}


@pytest.mark.asyncio
@respx.mock
async def test_async_bulk_domains_lookup():
    respx.post(f"{BASE_URL}/domains/bulk").mock(return_value=httpx.Response(200, json=BULK_RESPONSE))

    async with AsyncRdapApi("test-key", base_url=BASE_URL) as api:
        result = await api.bulk_domains(["google.com"])

    assert isinstance(result, BulkDomainResponse)
    assert result.summary.successful == 1
    assert result.results[0].data is not None
    assert result.results[0].data.domain == "google.com"


@pytest.mark.asyncio
@respx.mock
async def test_async_bulk_domains_plan_upgrade_required():
    respx.post(f"{BASE_URL}/domains/bulk").mock(
        return_value=httpx.Response(
            403, json={"error": "plan_upgrade_required", "message": "Bulk lookups require a Pro or Business plan."}
        )
    )

    async with AsyncRdapApi("test-key", base_url=BASE_URL) as api:
        with pytest.raises(SubscriptionRequiredError) as exc_info:
            await api.bulk_domains(["google.com"])

    assert exc_info.value.error == "plan_upgrade_required"
