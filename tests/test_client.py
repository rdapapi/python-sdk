"""Tests for the synchronous RDAP API client."""

import httpx
import pytest
import respx

from rdapapi import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    RdapApi,
    SubscriptionRequiredError,
    UpstreamError,
    ValidationError,
)

BASE_URL = "https://rdapapi.io/api/v1"

DOMAIN_RESPONSE = {
    "domain": "google.com",
    "unicode_name": None,
    "handle": "2138514_DOMAIN_COM-VRSN",
    "status": ["client delete prohibited"],
    "registrar": {
        "name": "MarkMonitor Inc.",
        "iana_id": "292",
        "abuse_email": "abusecomplaints@markmonitor.com",
        "abuse_phone": "+1.2086851750",
        "url": "http://www.markmonitor.com",
    },
    "dates": {
        "registered": "1997-09-15T04:00:00Z",
        "expires": "2028-09-14T04:00:00Z",
        "updated": "2019-09-09T15:39:04Z",
    },
    "nameservers": ["ns1.google.com", "ns2.google.com"],
    "dnssec": False,
    "entities": {},
    "meta": {
        "rdap_server": "https://rdap.verisign.com/com/v1/",
        "raw_rdap_url": "https://rdap.verisign.com/com/v1/domain/google.com",
        "cached": True,
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
    "dates": {"registered": "2023-12-28T17:24:33-05:00", "expires": None, "updated": "2023-12-28T17:24:56-05:00"},
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

ASN_RESPONSE = {
    "handle": "AS15169",
    "name": "GOOGLE",
    "type": None,
    "start_autnum": 15169,
    "end_autnum": 15169,
    "status": ["active"],
    "dates": {"registered": "2000-03-30T00:00:00-05:00", "expires": None, "updated": "2012-02-24T09:44:34-05:00"},
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

NS_RESPONSE = {
    "ldh_name": "ns1.google.com",
    "unicode_name": None,
    "handle": None,
    "ip_addresses": {"v4": ["216.239.32.10"], "v6": ["2001:4860:4802:32::a"]},
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
    "address": "1600 Amphitheatre Parkway\nMountain View\nCA\n94043\nUS",
    "contact_url": None,
    "country_code": None,
    "roles": [],
    "status": [],
    "dates": {"registered": "2000-03-30T00:00:00-04:00", "expires": None, "updated": "2019-10-31T15:45:45-04:00"},
    "remarks": [{"title": "Registration Comments", "description": "Please note..."}],
    "port43": "whois.arin.net",
    "public_ids": [{"type": "ARIN OrgID", "identifier": "GOGL"}],
    "entities": {
        "abuse": {
            "handle": "ABUSE5250-ARIN",
            "name": "Abuse",
            "organization": None,
            "email": "network-abuse@google.com",
            "phone": "+1-650-253-0000",
            "address": None,
            "contact_url": None,
            "country_code": None,
        },
    },
    "autnums": [{"handle": "AS15169", "name": "GOOGLE", "start_autnum": 15169, "end_autnum": 15169}],
    "networks": [
        {
            "handle": "NET-8-8-8-0-2",
            "name": "GOGL",
            "start_address": "8.8.8.0",
            "end_address": "8.8.8.255",
            "ip_version": "v4",
            "cidr": ["8.8.8.0/24"],
        },
    ],
    "meta": {
        "rdap_server": "https://rdap.arin.net/registry/",
        "raw_rdap_url": "https://rdap.arin.net/registry/entity/GOGL",
        "cached": False,
        "cache_expires": "2026-02-24T15:30:00Z",
    },
}


@respx.mock
def test_domain_lookup():
    respx.get(f"{BASE_URL}/domain/google.com").mock(return_value=httpx.Response(200, json=DOMAIN_RESPONSE))

    api = RdapApi("test-key", base_url=BASE_URL)
    result = api.domain("google.com")

    assert result.domain == "google.com"
    assert result.registrar.name == "MarkMonitor Inc."
    assert result.registrar.iana_id == "292"
    assert result.dates.registered == "1997-09-15T04:00:00Z"
    assert result.nameservers == ["ns1.google.com", "ns2.google.com"]
    assert result.dnssec is False
    assert result.meta.cached is True
    api.close()


@respx.mock
def test_domain_lookup_with_follow():
    route = respx.get(f"{BASE_URL}/domain/google.com", params={"follow": "true"}).mock(
        return_value=httpx.Response(200, json=DOMAIN_RESPONSE)
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    api.domain("google.com", follow=True)

    assert route.called
    api.close()


@respx.mock
def test_ip_lookup():
    respx.get(f"{BASE_URL}/ip/8.8.8.8").mock(return_value=httpx.Response(200, json=IP_RESPONSE))

    api = RdapApi("test-key", base_url=BASE_URL)
    result = api.ip("8.8.8.8")

    assert result.handle == "NET-8-8-8-0-2"
    assert result.name == "GOGL"
    assert result.cidr == ["8.8.8.0/24"]
    assert result.ip_version == "v4"
    assert result.port43 == "whois.arin.net"
    api.close()


@respx.mock
def test_asn_lookup():
    respx.get(f"{BASE_URL}/asn/15169").mock(return_value=httpx.Response(200, json=ASN_RESPONSE))

    api = RdapApi("test-key", base_url=BASE_URL)
    result = api.asn(15169)

    assert result.handle == "AS15169"
    assert result.name == "GOOGLE"
    assert result.start_autnum == 15169
    api.close()


@respx.mock
def test_asn_accepts_string_with_prefix():
    respx.get(f"{BASE_URL}/asn/15169").mock(return_value=httpx.Response(200, json=ASN_RESPONSE))

    api = RdapApi("test-key", base_url=BASE_URL)
    result = api.asn("AS15169")

    assert result.handle == "AS15169"
    api.close()


@respx.mock
def test_nameserver_lookup():
    respx.get(f"{BASE_URL}/nameserver/ns1.google.com").mock(return_value=httpx.Response(200, json=NS_RESPONSE))

    api = RdapApi("test-key", base_url=BASE_URL)
    result = api.nameserver("ns1.google.com")

    assert result.ldh_name == "ns1.google.com"
    assert result.ip_addresses.v4 == ["216.239.32.10"]
    assert result.ip_addresses.v6 == ["2001:4860:4802:32::a"]
    api.close()


@respx.mock
def test_entity_lookup():
    respx.get(f"{BASE_URL}/entity/GOGL").mock(return_value=httpx.Response(200, json=ENTITY_RESPONSE))

    api = RdapApi("test-key", base_url=BASE_URL)
    result = api.entity("GOGL")

    assert result.handle == "GOGL"
    assert result.name == "Google LLC"
    assert result.entities.abuse is not None
    assert result.entities.abuse.email == "network-abuse@google.com"
    assert result.autnums[0].handle == "AS15169"
    assert result.networks[0].cidr == ["8.8.8.0/24"]
    assert result.public_ids[0].identifier == "GOGL"
    api.close()


@respx.mock
def test_context_manager():
    respx.get(f"{BASE_URL}/domain/google.com").mock(return_value=httpx.Response(200, json=DOMAIN_RESPONSE))

    with RdapApi("test-key", base_url=BASE_URL) as api:
        result = api.domain("google.com")
        assert result.domain == "google.com"


@respx.mock
def test_custom_base_url():
    respx.get("http://localhost/api/v1/domain/test.com").mock(return_value=httpx.Response(200, json=DOMAIN_RESPONSE))

    api = RdapApi("test-key", base_url="http://localhost/api/v1")
    result = api.domain("test.com")
    assert result.domain == "google.com"  # fixture data
    api.close()


@respx.mock
def test_authentication_error():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(401, json={"error": "unauthenticated", "message": "Invalid or missing API token."})
    )

    api = RdapApi("bad-key", base_url=BASE_URL)
    with pytest.raises(AuthenticationError) as exc_info:
        api.domain("test.com")

    assert exc_info.value.status_code == 401
    assert exc_info.value.error == "unauthenticated"
    api.close()


@respx.mock
def test_subscription_required_error():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(
            403, json={"error": "subscription_required", "message": "An active subscription is required."}
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(SubscriptionRequiredError) as exc_info:
        api.domain("test.com")

    assert exc_info.value.status_code == 403
    api.close()


@respx.mock
def test_not_found_error():
    respx.get(f"{BASE_URL}/domain/nonexistent.example").mock(
        return_value=httpx.Response(404, json={"error": "not_found", "message": "No RDAP data found."})
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(NotFoundError) as exc_info:
        api.domain("nonexistent.example")

    assert exc_info.value.status_code == 404
    api.close()


@respx.mock
def test_rate_limit_error():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(
            429,
            json={"error": "rate_limit_exceeded", "message": "Rate limit exceeded."},
            headers={"Retry-After": "60"},
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(RateLimitError) as exc_info:
        api.domain("test.com")

    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after == 60
    api.close()


@respx.mock
def test_validation_error():
    respx.get(f"{BASE_URL}/domain/invalid").mock(
        return_value=httpx.Response(
            400, json={"error": "invalid_domain", "message": "The provided domain name is not valid."}
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(ValidationError) as exc_info:
        api.domain("invalid")

    assert exc_info.value.status_code == 400
    api.close()


@respx.mock
def test_upstream_error():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(502, json={"error": "lookup_failed", "message": "RDAP lookup failed."})
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(UpstreamError) as exc_info:
        api.domain("test.com")

    assert exc_info.value.status_code == 502
    api.close()


@respx.mock
def test_auth_header_sent():
    route = respx.get(f"{BASE_URL}/domain/google.com").mock(return_value=httpx.Response(200, json=DOMAIN_RESPONSE))

    api = RdapApi("my-secret-key", base_url=BASE_URL)
    api.domain("google.com")

    assert route.calls[0].request.headers["authorization"] == "Bearer my-secret-key"
    api.close()
