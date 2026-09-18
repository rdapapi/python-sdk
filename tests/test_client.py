"""Tests for the synchronous RDAP API client."""

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
import pytest
import respx

from rdapapi import (
    AuthenticationError,
    GatewayTimeoutError,
    MethodNotAllowedError,
    NotFoundError,
    NotSupportedError,
    PayloadTooLargeError,
    PlanUpgradeRequiredError,
    RateLimitError,
    RdapApi,
    RdapApiError,
    RequestFailedError,
    ServerError,
    SubscriptionRequiredError,
    TemporarilyUnavailableError,
    UpstreamError,
    ValidationError,
)
from rdapapi.models import BulkDomainResponse, TldListResponse, TldResponse

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
        "abuse_phone": "+12086851750",
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
        "server": "rdap.verisign.com",
        "source": "rdap",
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
    "geofeed": None,
    "remarks": [],
    "port43": "whois.arin.net",
    "meta": {
        "server": "rdap.arin.net",
        "source": "rdap",
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
        "server": "rdap.arin.net",
        "source": "rdap",
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
        "server": "rdap.verisign.com",
        "source": "rdap",
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
            "phone": "+16502530000",
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
        "server": "rdap.arin.net",
        "source": "rdap",
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
def test_forbidden_is_a_subscription_required_error_branching_on_error():
    """A 403 IP block shares the subscription class, so only ``error`` tells them apart."""
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(403, json={"error": "forbidden", "message": "This IP is temporarily blocked."})
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(SubscriptionRequiredError) as exc_info:
        api.domain("test.com")

    assert exc_info.value.status_code == 403
    assert exc_info.value.error == "forbidden"
    assert not isinstance(exc_info.value, PlanUpgradeRequiredError)
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
    assert not isinstance(exc_info.value, NotSupportedError)
    api.close()


@respx.mock
def test_not_supported_error_raised_on_unsupported_tld():
    respx.get(f"{BASE_URL}/domain/example.nope").mock(
        return_value=httpx.Response(
            404,
            json={"error": "not_supported", "message": "The TLD '.nope' is not supported."},
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(NotSupportedError) as exc_info:
        api.domain("example.nope")

    assert exc_info.value.status_code == 404
    assert exc_info.value.error == "not_supported"
    # Backwards compatible: NotSupportedError IS a NotFoundError.
    assert isinstance(exc_info.value, NotFoundError)
    api.close()


@respx.mock
def test_not_supported_error_on_ip_lookup():
    respx.get(f"{BASE_URL}/ip/203.0.113.1").mock(
        return_value=httpx.Response(
            404,
            json={"error": "not_supported", "message": "No RIR covers this IP range."},
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(NotSupportedError):
        api.ip("203.0.113.1")
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
def test_temporarily_unavailable_error():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(
            503,
            json={"error": "temporarily_unavailable", "message": "Data for this domain is temporarily unavailable."},
            headers={"Retry-After": "300"},
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(TemporarilyUnavailableError) as exc_info:
        api.domain("test.com")

    assert exc_info.value.status_code == 503
    assert exc_info.value.retry_after == 300
    api.close()


@respx.mock
def test_temporarily_unavailable_error_without_retry_after():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(
            503,
            json={"error": "temporarily_unavailable", "message": "Data for this domain is temporarily unavailable."},
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(TemporarilyUnavailableError) as exc_info:
        api.domain("test.com")

    assert exc_info.value.status_code == 503
    assert exc_info.value.retry_after is None
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


def test_empty_api_key_raises():
    with pytest.raises(ValueError, match="non-empty"):
        RdapApi("")


@respx.mock
def test_non_json_error_body():
    respx.get(f"{BASE_URL}/domain/test.com").mock(return_value=httpx.Response(500, text="Internal Server Error"))

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(RdapApiError) as exc_info:
        api.domain("test.com")

    assert exc_info.value.status_code == 500
    assert exc_info.value.error == "unknown_error"
    api.close()


@respx.mock
def test_auth_header_sent():
    route = respx.get(f"{BASE_URL}/domain/google.com").mock(return_value=httpx.Response(200, json=DOMAIN_RESPONSE))

    api = RdapApi("my-secret-key", base_url=BASE_URL)
    api.domain("google.com")

    assert route.calls[0].request.headers["authorization"] == "Bearer my-secret-key"
    api.close()


# === Bulk Domain Lookups ===

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
                "nameservers": ["ns1.google.com", "ns2.google.com"],
                "dnssec": False,
                "entities": {},
            },
            "meta": {
                "server": "rdap.verisign.com",
                "source": "rdap",
                "rdap_server": "https://rdap.verisign.com/com/v1/",
                "raw_rdap_url": "https://rdap.verisign.com/com/v1/domain/google.com",
                "cached": False,
                "cache_expires": "2026-02-25T15:30:00Z",
            },
        },
        {
            "domain": "invalid..com",
            "status": "error",
            "error": "invalid_domain",
            "message": "The provided domain name is not valid.",
        },
    ],
    "summary": {"total": 2, "successful": 1, "failed": 1},
}


@respx.mock
def test_bulk_domains_lookup():
    respx.post(f"{BASE_URL}/domains/bulk").mock(return_value=httpx.Response(200, json=BULK_RESPONSE))

    api = RdapApi("test-key", base_url=BASE_URL)
    result = api.bulk_domains(["google.com", "invalid..com"])

    assert isinstance(result, BulkDomainResponse)
    assert result.summary.total == 2
    assert result.summary.successful == 1
    assert result.summary.failed == 1

    # Successful result has data as DomainResponse
    assert result.results[0].status == "success"
    assert result.results[0].data is not None
    assert result.results[0].data.domain == "google.com"
    assert result.results[0].data.registrar.name == "MarkMonitor Inc."
    assert result.results[0].data.meta.rdap_server == "https://rdap.verisign.com/com/v1/"

    # Error result has error info
    assert result.results[1].status == "error"
    assert result.results[1].error == "invalid_domain"
    assert result.results[1].data is None

    api.close()


@respx.mock
def test_bulk_domains_with_follow():
    route = respx.post(f"{BASE_URL}/domains/bulk").mock(return_value=httpx.Response(200, json=BULK_RESPONSE))

    api = RdapApi("test-key", base_url=BASE_URL)
    api.bulk_domains(["google.com"], follow=True)

    request = route.calls[0].request
    import json

    body = json.loads(request.content)
    assert body["domains"] == ["google.com"]
    assert body["follow"] is True
    api.close()


@respx.mock
def test_bulk_domains_without_follow_omits_key():
    route = respx.post(f"{BASE_URL}/domains/bulk").mock(return_value=httpx.Response(200, json=BULK_RESPONSE))

    api = RdapApi("test-key", base_url=BASE_URL)
    api.bulk_domains(["google.com"])

    request = route.calls[0].request
    import json

    body = json.loads(request.content)
    assert "follow" not in body
    api.close()


@respx.mock
def test_bulk_domains_plan_upgrade_required():
    respx.post(f"{BASE_URL}/domains/bulk").mock(
        return_value=httpx.Response(
            403, json={"error": "plan_upgrade_required", "message": "Bulk lookups require a Pro or Business plan."}
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(SubscriptionRequiredError) as exc_info:
        api.bulk_domains(["google.com"])

    assert exc_info.value.status_code == 403
    assert exc_info.value.error == "plan_upgrade_required"
    api.close()


@respx.mock
def test_bulk_domains_auth_error():
    respx.post(f"{BASE_URL}/domains/bulk").mock(
        return_value=httpx.Response(401, json={"error": "unauthenticated", "message": "Invalid or missing API token."})
    )

    api = RdapApi("bad-key", base_url=BASE_URL)
    with pytest.raises(AuthenticationError):
        api.bulk_domains(["google.com"])
    api.close()


@respx.mock
def test_bulk_domains_rate_limit_error():
    respx.post(f"{BASE_URL}/domains/bulk").mock(
        return_value=httpx.Response(
            429,
            json={"error": "rate_limit_exceeded", "message": "Rate limit exceeded."},
            headers={"Retry-After": "60"},
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(RateLimitError) as exc_info:
        api.bulk_domains(["google.com"])

    assert exc_info.value.retry_after == 60
    api.close()


# === TLDs ===

TLDS_RESPONSE = {
    "data": [
        {
            "tld": "com",
            "supported_since": "2026-03-07T00:00:00Z",
            "protocol": "rdap",
            "server": "rdap.verisign.com",
            "rdap_server_host": "rdap.verisign.com",
            "rdap_server_url": "https://rdap.verisign.com/com/v1/",
            "field_availability": {
                "registrar": "sometimes",
                "registered_at": "always",
                "expires_at": "always",
                "nameservers": "always",
                "status": "always",
            },
        },
        {
            "tld": "fr",
            "supported_since": "2026-03-07T00:00:00Z",
            "protocol": "rdap",
            "server": "rdap.nic.fr",
            "rdap_server_host": "rdap.nic.fr",
            "rdap_server_url": "https://rdap.nic.fr/",
            "field_availability": None,
        },
    ],
    "meta": {
        "computed_at": "2026-04-22T10:00:00Z",
        "count": 2,
        "coverage": 0.5,
        "thresholds": {"always": 0.99, "usually": 0.8, "sometimes": 0.0},
    },
}

TLD_RESPONSE = {
    "data": {
        "tld": "com",
        "supported_since": "2026-03-07T00:00:00Z",
        "protocol": "rdap",
        "server": "rdap.verisign.com",
        "rdap_server_host": "rdap.verisign.com",
        "rdap_server_url": "https://rdap.verisign.com/com/v1/",
        "field_availability": {
            "registrar": "sometimes",
            "registered_at": "always",
            "expires_at": "always",
            "nameservers": "always",
            "status": "always",
        },
    },
    "meta": {
        "computed_at": "2026-04-22T10:00:00Z",
        "thresholds": {"always": 0.99, "usually": 0.8, "sometimes": 0.0},
    },
}


@respx.mock
def test_tlds_list():
    respx.get(f"{BASE_URL}/tlds").mock(return_value=httpx.Response(200, json=TLDS_RESPONSE, headers={"ETag": '"abc"'}))

    api = RdapApi("test-key", base_url=BASE_URL)
    result = api.tlds()

    assert isinstance(result, TldListResponse)
    assert result.meta.count == 2
    assert result.meta.coverage == 0.5
    assert result.meta.thresholds.always == 0.99
    assert result.data[0].tld == "com"
    assert result.data[0].field_availability is not None
    assert result.data[0].field_availability.registered_at == "always"
    assert result.data[1].field_availability is None
    assert result.etag == '"abc"'
    api.close()


@respx.mock
def test_tlds_list_with_since_and_server():
    route = respx.get(f"{BASE_URL}/tlds").mock(return_value=httpx.Response(200, json=TLDS_RESPONSE))

    api = RdapApi("test-key", base_url=BASE_URL)
    api.tlds(since="2026-04-01T00:00:00Z", server="rdap.verisign.com")

    request = route.calls[0].request
    assert request.url.params["since"] == "2026-04-01T00:00:00Z"
    assert request.url.params["server"] == "rdap.verisign.com"
    api.close()


@respx.mock
def test_tlds_list_304_returns_none():
    respx.get(f"{BASE_URL}/tlds").mock(return_value=httpx.Response(304))

    api = RdapApi("test-key", base_url=BASE_URL)
    result = api.tlds(if_none_match='"abc"')

    assert result is None
    api.close()


@respx.mock
def test_tlds_list_sends_if_none_match_header():
    route = respx.get(f"{BASE_URL}/tlds").mock(return_value=httpx.Response(304))

    api = RdapApi("test-key", base_url=BASE_URL)
    api.tlds(if_none_match='"etag-value"')

    assert route.calls[0].request.headers["if-none-match"] == '"etag-value"'
    api.close()


@respx.mock
def test_tld_show():
    respx.get(f"{BASE_URL}/tlds/com").mock(
        return_value=httpx.Response(200, json=TLD_RESPONSE, headers={"ETag": '"com-1"'})
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    result = api.tld("com")

    assert isinstance(result, TldResponse)
    assert result.data.tld == "com"
    assert result.meta.thresholds.usually == 0.8
    assert result.etag == '"com-1"'
    api.close()


@respx.mock
def test_tld_show_304_returns_none():
    respx.get(f"{BASE_URL}/tlds/com").mock(return_value=httpx.Response(304))

    api = RdapApi("test-key", base_url=BASE_URL)
    assert api.tld("com", if_none_match='"com-1"') is None
    api.close()


@respx.mock
def test_tld_show_not_found():
    respx.get(f"{BASE_URL}/tlds/nope").mock(
        return_value=httpx.Response(
            404, json={"error": "not_found", "message": "No RDAP server is registered for the TLD 'nope'."}
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(NotFoundError):
        api.tld("nope")
    api.close()


# === Health check ===


@respx.mock
def test_ping():
    respx.get(f"{BASE_URL}/ping").mock(return_value=httpx.Response(200, json={"status": "ok"}))

    api = RdapApi("test-key", base_url=BASE_URL)
    assert api.ping().status == "ok"
    api.close()


# === WHOIS fallback ===

WHOIS_DOMAIN_RESPONSE = {
    "domain": "google.it",
    "unicode_name": None,
    "handle": None,
    "status": ["active"],
    "registrar": {
        "name": "MarkMonitor International Limited",
        "iana_id": None,
        "abuse_email": None,
        "abuse_phone": None,
        "url": "https://www.markmonitor.com/",
    },
    "dates": {"registered": "1999-12-10T00:00:00Z", "expires": "2027-04-21T00:00:00Z", "updated": None},
    "nameservers": ["ns1.google.com"],
    "dnssec": False,
    "entities": {},
    "meta": {
        "server": "whois.nic.it",
        "source": "whois",
        "cached": True,
        "cache_expires": "2026-09-19T11:24:58Z",
    },
}


@respx.mock
def test_domain_answered_over_whois():
    respx.get(f"{BASE_URL}/domain/google.it").mock(return_value=httpx.Response(200, json=WHOIS_DOMAIN_RESPONSE))

    api = RdapApi("test-key", base_url=BASE_URL)
    result = api.domain("google.it")

    assert result.meta.source == "whois"
    assert result.meta.server == "whois.nic.it"
    assert result.meta.rdap_server is None
    assert result.meta.raw_rdap_url is None
    api.close()


@respx.mock
def test_domain_refusing_whois_fallback():
    route = respx.get(f"{BASE_URL}/domain/google.it", params={"whois": "false"}).mock(
        return_value=httpx.Response(
            404, json={"error": "not_supported", "message": "Unsupported TLD for domain: google.it"}
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(NotSupportedError):
        api.domain("google.it", whois=False)

    assert route.called
    api.close()


@respx.mock
def test_domain_follow_and_whois_params_travel_together():
    route = respx.get(f"{BASE_URL}/domain/google.com", params={"follow": "true", "whois": "false"}).mock(
        return_value=httpx.Response(200, json=DOMAIN_RESPONSE)
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    api.domain("google.com", follow=True, whois=False)

    assert route.called
    api.close()


@respx.mock
def test_bulk_domains_whois_false_sent_in_body():
    route = respx.post(f"{BASE_URL}/domains/bulk").mock(return_value=httpx.Response(200, json=BULK_RESPONSE))

    api = RdapApi("test-key", base_url=BASE_URL)
    api.bulk_domains(["google.it"], whois=False)

    import json

    body = json.loads(route.calls[0].request.content)
    assert body["whois"] is False
    api.close()


@respx.mock
def test_bulk_domains_default_omits_whois():
    route = respx.post(f"{BASE_URL}/domains/bulk").mock(return_value=httpx.Response(200, json=BULK_RESPONSE))

    api = RdapApi("test-key", base_url=BASE_URL)
    api.bulk_domains(["google.com"])

    import json

    assert "whois" not in json.loads(route.calls[0].request.content)
    api.close()


@respx.mock
def test_bulk_failed_entry_keeps_its_partial_meta():
    payload = {
        "results": [
            {
                "domain": "example.com",
                "status": "error",
                "error": "lookup_failed",
                "message": "RDAP lookup failed.",
                "meta": {"server": "rdap.verisign.com", "source": "rdap"},
            },
        ],
        "summary": {"total": 1, "successful": 0, "failed": 1},
    }
    respx.post(f"{BASE_URL}/domains/bulk").mock(return_value=httpx.Response(200, json=payload))

    api = RdapApi("test-key", base_url=BASE_URL)
    result = api.bulk_domains(["example.com"])

    assert result.results[0].data is None
    assert result.results[0].meta is not None
    assert result.results[0].meta.server == "rdap.verisign.com"
    assert result.results[0].meta.cached is None
    api.close()


@respx.mock
def test_bulk_successful_entry_exposes_meta_on_both_levels():
    respx.post(f"{BASE_URL}/domains/bulk").mock(return_value=httpx.Response(200, json=BULK_RESPONSE))

    api = RdapApi("test-key", base_url=BASE_URL)
    result = api.bulk_domains(["google.com"])

    assert result.results[0].meta is not None
    assert result.results[0].data is not None
    assert result.results[0].meta.server == result.results[0].data.meta.server
    api.close()


# === IP lookups ===


@respx.mock
def test_ip_lookup_accepts_a_cidr_block():
    route = respx.get(f"{BASE_URL}/ip/8.8.8.0/24").mock(return_value=httpx.Response(200, json=IP_RESPONSE))

    api = RdapApi("test-key", base_url=BASE_URL)
    result = api.ip("8.8.8.0/24")

    assert route.called
    assert result.geofeed is None
    api.close()


@respx.mock
def test_ip_lookup_exposes_geofeed():
    payload = {**IP_RESPONSE, "geofeed": "https://geofeed.ipxo.com/geofeed.txt"}
    respx.get(f"{BASE_URL}/ip/1.1.1.0/24").mock(return_value=httpx.Response(200, json=payload))

    api = RdapApi("test-key", base_url=BASE_URL)
    result = api.ip("1.1.1.0/24")

    assert result.geofeed == "https://geofeed.ipxo.com/geofeed.txt"
    api.close()


# === Error codes ===


@respx.mock
def test_plan_upgrade_required_error():
    respx.post(f"{BASE_URL}/domains/bulk").mock(
        return_value=httpx.Response(
            403, json={"error": "plan_upgrade_required", "message": "Bulk lookups require a Pro or Business plan."}
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(PlanUpgradeRequiredError) as exc_info:
        api.bulk_domains(["google.com"])

    # Backwards compatible: PlanUpgradeRequiredError IS a SubscriptionRequiredError.
    assert isinstance(exc_info.value, SubscriptionRequiredError)
    api.close()


@respx.mock
def test_request_failed_error_carries_field_errors():
    respx.post(f"{BASE_URL}/domains/bulk").mock(
        return_value=httpx.Response(
            422,
            json={
                "error": "request_failed",
                "message": "The domains field must not have more than 10 items.",
                "errors": {"domains": ["The domains field must not have more than 10 items."]},
            },
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(RequestFailedError) as exc_info:
        api.bulk_domains(["a.com"] * 11)

    assert exc_info.value.status_code == 422
    assert exc_info.value.errors["domains"] == ["The domains field must not have more than 10 items."]
    api.close()


@respx.mock
def test_request_failed_error_without_errors_object():
    respx.post(f"{BASE_URL}/domains/bulk").mock(
        return_value=httpx.Response(422, json={"error": "request_failed", "message": "Validation failed."})
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(RequestFailedError) as exc_info:
        api.bulk_domains(["a.com"])

    assert exc_info.value.errors == {}
    api.close()


@respx.mock
def test_method_not_allowed_error():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(405, json={"error": "method_not_allowed", "message": "Method not allowed."})
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(MethodNotAllowedError):
        api.domain("test.com")
    api.close()


@respx.mock
def test_payload_too_large_error():
    respx.post(f"{BASE_URL}/domains/bulk").mock(
        return_value=httpx.Response(413, json={"error": "payload_too_large", "message": "Payload too large."})
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(PayloadTooLargeError):
        api.bulk_domains(["a.com"])
    api.close()


@respx.mock
def test_gateway_timeout_error():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(
            504, json={"error": "gateway_timeout", "message": "The request did not complete in time."}
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(GatewayTimeoutError) as exc_info:
        api.domain("test.com")

    assert isinstance(exc_info.value, ServerError)
    api.close()


@respx.mock
def test_unmapped_server_error():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(500, json={"error": "server_error", "message": "Something went wrong."})
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(ServerError) as exc_info:
        api.domain("test.com")

    assert exc_info.value.status_code == 500
    assert exc_info.value.error == "server_error"
    api.close()


@respx.mock
def test_non_json_error_body_from_the_edge_is_a_server_error():
    respx.get(f"{BASE_URL}/domain/test.com").mock(return_value=httpx.Response(502, html="<html>Bad gateway</html>"))

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(UpstreamError) as exc_info:
        api.domain("test.com")

    assert isinstance(exc_info.value, ServerError)
    assert exc_info.value.error == "unknown_error"
    api.close()


@respx.mock
def test_json_error_body_that_is_not_an_object():
    respx.get(f"{BASE_URL}/domain/test.com").mock(return_value=httpx.Response(503, json=["nope"]))

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(TemporarilyUnavailableError) as exc_info:
        api.domain("test.com")

    assert exc_info.value.error == "unknown_error"
    assert exc_info.value.retry_after is None
    api.close()


@respx.mock
def test_retry_after_read_from_the_body():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(
            429,
            json={"error": "rate_limit_exceeded", "message": "Rate limit exceeded.", "retry_after": 30},
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(RateLimitError) as exc_info:
        api.domain("test.com")

    assert exc_info.value.retry_after == 30
    api.close()


@respx.mock
def test_retry_after_on_upstream_error():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(
            502,
            json={"error": "lookup_failed", "message": "RDAP lookup failed.", "retry_after": 60},
            headers={"Retry-After": "60"},
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(UpstreamError) as exc_info:
        api.domain("test.com")

    assert exc_info.value.retry_after == 60
    api.close()


def _http_date(seconds_from_now: int, *, tz: bool = True) -> str:
    """An RFC 9110 HTTP-date that many seconds away, as a registry would send it."""
    when = datetime.now(timezone.utc) + timedelta(seconds=seconds_from_now)
    return format_datetime(when, usegmt=True) if tz else format_datetime(when.replace(tzinfo=None))


@respx.mock
def test_retry_after_http_date_header_is_read_as_seconds():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(
            429,
            json={"error": "too_many_requests", "message": "Slow down."},
            headers={"Retry-After": _http_date(120)},
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(RateLimitError) as exc_info:
        api.domain("test.com")

    assert 115 <= exc_info.value.retry_after <= 120
    api.close()


@respx.mock
def test_retry_after_http_date_without_a_zone_is_read_as_utc():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(
            503,
            json={"error": "temporarily_unavailable", "message": "Registry throttling us."},
            headers={"Retry-After": _http_date(300, tz=False)},
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(TemporarilyUnavailableError) as exc_info:
        api.domain("test.com")

    assert 295 <= exc_info.value.retry_after <= 300
    api.close()


@respx.mock
def test_retry_after_http_date_in_the_past_is_zero():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(
            429,
            json={"error": "too_many_requests", "message": "Slow down."},
            headers={"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"},
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(RateLimitError) as exc_info:
        api.domain("test.com")

    assert exc_info.value.retry_after == 0
    api.close()


@respx.mock
def test_retry_after_header_wins_over_the_body():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(
            429,
            json={"error": "rate_limit_exceeded", "message": "Rate limit exceeded.", "retry_after": 30},
            headers={"Retry-After": "60"},
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(RateLimitError) as exc_info:
        api.domain("test.com")

    assert exc_info.value.retry_after == 60
    api.close()


@respx.mock
def test_retry_after_zero_header_is_not_treated_as_absent():
    """``Retry-After: 0`` means retry now, so it must beat the body's estimate."""
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(
            429,
            json={"error": "rate_limit_exceeded", "message": "Rate limit exceeded.", "retry_after": 30},
            headers={"Retry-After": "0"},
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(RateLimitError) as exc_info:
        api.domain("test.com")

    assert exc_info.value.retry_after == 0
    api.close()


@respx.mock
def test_retry_after_unparseable_header_falls_back_to_the_body():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(
            429,
            json={"error": "rate_limit_exceeded", "message": "Rate limit exceeded.", "retry_after": 30},
            headers={"Retry-After": "soon"},
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(RateLimitError) as exc_info:
        api.domain("test.com")

    assert exc_info.value.retry_after == 30
    api.close()


@respx.mock
def test_retry_after_unparseable_header_and_no_body_value():
    respx.get(f"{BASE_URL}/domain/test.com").mock(
        return_value=httpx.Response(
            429,
            json={"error": "too_many_requests", "message": "Slow down."},
            headers={"Retry-After": "soon"},
        )
    )

    api = RdapApi("test-key", base_url=BASE_URL)
    with pytest.raises(RateLimitError) as exc_info:
        api.domain("test.com")

    assert exc_info.value.retry_after is None
    api.close()


# === TLDs served over WHOIS ===


@respx.mock
def test_tlds_list_includes_whois_served_tlds():
    payload = {
        "data": [
            {
                "tld": "it",
                "protocol": "whois",
                "supported_since": "2026-05-13T11:21:03Z",
                "server": "whois.nic.it",
                "rdap_server_host": None,
                "rdap_server_url": None,
                "field_availability": None,
            },
        ],
        "meta": {
            "computed_at": "2026-09-18T10:00:00Z",
            "count": 1,
            "coverage": 1.0,
            "thresholds": {"always": 0.99, "usually": 0.8, "sometimes": 0.0},
        },
    }
    respx.get(f"{BASE_URL}/tlds").mock(return_value=httpx.Response(200, json=payload))

    api = RdapApi("test-key", base_url=BASE_URL)
    result = api.tlds(server="whois.nic.it")

    assert result.data[0].protocol == "whois"
    assert result.data[0].server == "whois.nic.it"
    assert result.data[0].rdap_server_host is None
    assert result.data[0].rdap_server_url is None
    assert result.data[0].field_availability is None
    api.close()
