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


IP_RESPONSE = {
    "handle": "NET-8-8-8-0-2",
    "name": "GOGL",
    "type": "DIRECT ALLOCATION",
    "start_address": "8.8.8.0",
    "end_address": "8.8.8.255",
    "ip_version": "v4",
    "parent_handle": "NET-8-0-0-0-0",
    "country": None,
    "status": ["active"],
    "dates": {"registered": "2023-12-28T17:24:33-05:00", "expires": None, "updated": None},
    "entities": {},
    "cidr": ["8.8.8.0/24"],
    "remarks": [],
    "port43": "whois.arin.net",
    "meta": {
        "rdap_server": "https://rdap.arin.net/registry/",
        "raw_rdap_url": "https://rdap.arin.net/registry/ip/8.8.8.8",
        "cached": False,
        "cache_expires": "2026-02-24T15:30:00Z",
    },
}

NS_RESPONSE = {
    "ldh_name": "ns1.google.com",
    "unicode_name": None,
    "handle": None,
    "ip_addresses": {"v4": ["216.239.32.10"], "v6": []},
    "status": [],
    "dates": {"registered": None, "expires": None, "updated": None},
    "entities": {},
    "meta": {
        "rdap_server": "https://rdap.verisign.com/com/v1/",
        "raw_rdap_url": "https://rdap.verisign.com/com/v1/nameserver/ns1.google.com",
        "cached": False,
        "cache_expires": "2026-02-24T15:30:00Z",
    },
}

ENTITY_RESPONSE = {
    "handle": "GOGL",
    "name": "Google LLC",
    "organization": None,
    "email": None,
    "phone": None,
    "address": None,
    "contact_url": None,
    "country_code": None,
    "roles": [],
    "status": [],
    "dates": {"registered": "2000-03-30T00:00:00-04:00", "expires": None, "updated": None},
    "remarks": [],
    "port43": "whois.arin.net",
    "public_ids": [],
    "entities": {},
    "autnums": [],
    "networks": [],
    "meta": {
        "rdap_server": "https://rdap.arin.net/registry/",
        "raw_rdap_url": "https://rdap.arin.net/registry/entity/GOGL",
        "cached": False,
        "cache_expires": "2026-02-24T15:30:00Z",
    },
}


@pytest.mark.asyncio
async def test_async_empty_api_key_raises():
    with pytest.raises(ValueError, match="non-empty"):
        AsyncRdapApi("")


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


@pytest.mark.asyncio
@respx.mock
async def test_async_ip_lookup():
    respx.get(f"{BASE_URL}/ip/8.8.8.8").mock(return_value=httpx.Response(200, json=IP_RESPONSE))

    async with AsyncRdapApi("test-key", base_url=BASE_URL) as api:
        result = await api.ip("8.8.8.8")

    assert result.handle == "NET-8-8-8-0-2"
    assert result.ip_version == "v4"


@pytest.mark.asyncio
@respx.mock
async def test_async_nameserver_lookup():
    respx.get(f"{BASE_URL}/nameserver/ns1.google.com").mock(return_value=httpx.Response(200, json=NS_RESPONSE))

    async with AsyncRdapApi("test-key", base_url=BASE_URL) as api:
        result = await api.nameserver("ns1.google.com")

    assert result.ldh_name == "ns1.google.com"


@pytest.mark.asyncio
@respx.mock
async def test_async_entity_lookup():
    respx.get(f"{BASE_URL}/entity/GOGL").mock(return_value=httpx.Response(200, json=ENTITY_RESPONSE))

    async with AsyncRdapApi("test-key", base_url=BASE_URL) as api:
        result = await api.entity("GOGL")

    assert result.handle == "GOGL"
    assert result.name == "Google LLC"


@pytest.mark.asyncio
@respx.mock
async def test_async_bulk_domains_with_follow():
    import json

    route = respx.post(f"{BASE_URL}/domains/bulk").mock(return_value=httpx.Response(200, json=BULK_RESPONSE))

    async with AsyncRdapApi("test-key", base_url=BASE_URL) as api:
        await api.bulk_domains(["google.com"], follow=True)

    body = json.loads(route.calls[0].request.content)
    assert body["follow"] is True
