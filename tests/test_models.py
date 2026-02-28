"""Tests for Pydantic model parsing."""

from rdapapi import (
    AsnResponse,
    BulkDomainResponse,
    Dates,
    DomainResponse,
    EntityResponse,
    IpResponse,
    NameserverResponse,
)


def test_domain_response_parses():
    data = {
        "domain": "example.com",
        "unicode_name": None,
        "handle": "EXAMPLE-HANDLE",
        "status": ["active"],
        "registrar": {
            "name": "Example Registrar",
            "iana_id": "1",
            "abuse_email": None,
            "abuse_phone": None,
            "url": None,
        },
        "dates": {"registered": "2020-01-01T00:00:00Z", "expires": "2025-01-01T00:00:00Z", "updated": None},
        "nameservers": ["ns1.example.com"],
        "dnssec": True,
        "entities": {
            "registrant": {
                "handle": "REG-1",
                "name": "John Doe",
                "organization": "Example Inc.",
                "email": "john@example.com",
                "phone": "+1-555-0100",
                "address": "123 Main St",
                "contact_url": None,
                "country_code": "US",
            },
        },
        "meta": {
            "rdap_server": "https://rdap.example.com/",
            "raw_rdap_url": "https://rdap.example.com/domain/example.com",
            "cached": False,
            "cache_expires": "2026-02-25T00:00:00Z",
        },
    }

    result = DomainResponse.model_validate(data)

    assert result.domain == "example.com"
    assert result.dnssec is True
    assert result.entities.registrant is not None
    assert result.entities.registrant.name == "John Doe"
    assert result.entities.registrant.country_code == "US"
    assert result.entities.administrative is None
    assert result.meta.rdap_server == "https://rdap.example.com/"


def test_domain_response_empty_entities():
    data = {
        "domain": "test.com",
        "unicode_name": None,
        "handle": None,
        "status": [],
        "registrar": {"name": None, "iana_id": None, "abuse_email": None, "abuse_phone": None, "url": None},
        "dates": {"registered": None, "expires": None, "updated": None},
        "nameservers": [],
        "dnssec": False,
        "entities": {},
        "meta": {
            "rdap_server": "https://rdap.example.com/",
            "raw_rdap_url": "https://rdap.example.com/domain/test.com",
            "cached": True,
            "cache_expires": "2026-02-25T00:00:00Z",
        },
    }

    result = DomainResponse.model_validate(data)

    assert result.entities.registrant is None
    assert result.entities.technical is None
    assert result.handle is None
    assert result.dates.registered is None


def test_ip_response_parses():
    data = {
        "handle": "NET-1-0-0-0-1",
        "name": "TEST-NET",
        "type": "DIRECT ALLOCATION",
        "start_address": "1.0.0.0",
        "end_address": "1.0.0.255",
        "ip_version": "v4",
        "parent_handle": "NET-1-0-0-0-0",
        "country": "AU",
        "status": ["active"],
        "dates": {"registered": "2020-01-01T00:00:00Z", "expires": None, "updated": None},
        "entities": {},
        "cidr": ["1.0.0.0/24"],
        "remarks": [{"title": "description", "description": "Test network"}],
        "port43": "whois.apnic.net",
        "meta": {
            "rdap_server": "https://rdap.apnic.net/",
            "raw_rdap_url": "https://rdap.apnic.net/ip/1.0.0.0",
            "cached": False,
            "cache_expires": "2026-02-25T00:00:00Z",
        },
    }

    result = IpResponse.model_validate(data)

    assert result.cidr == ["1.0.0.0/24"]
    assert result.country == "AU"
    assert result.remarks[0].description == "Test network"


def test_asn_response_parses():
    data = {
        "handle": "AS15169",
        "name": "GOOGLE",
        "type": None,
        "start_autnum": 15169,
        "end_autnum": 15169,
        "status": ["active"],
        "dates": {"registered": "2000-03-30T00:00:00Z", "expires": None, "updated": None},
        "entities": {},
        "remarks": [],
        "port43": "whois.arin.net",
        "meta": {
            "rdap_server": "https://rdap.arin.net/registry/",
            "raw_rdap_url": "https://rdap.arin.net/registry/autnum/15169",
            "cached": False,
            "cache_expires": "2026-02-25T00:00:00Z",
        },
    }

    result = AsnResponse.model_validate(data)

    assert result.start_autnum == 15169
    assert result.end_autnum == 15169
    assert result.type is None


def test_nameserver_response_parses():
    data = {
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
            "cache_expires": "2026-02-25T00:00:00Z",
        },
    }

    result = NameserverResponse.model_validate(data)

    assert result.ldh_name == "ns1.google.com"
    assert result.ip_addresses.v4 == ["216.239.32.10"]
    assert result.handle is None


def test_entity_response_with_autnums_and_networks():
    data = {
        "handle": "GOGL",
        "name": "Google LLC",
        "organization": None,
        "email": None,
        "phone": None,
        "address": "1600 Amphitheatre Parkway",
        "contact_url": None,
        "country_code": None,
        "roles": [],
        "status": [],
        "dates": {"registered": "2000-03-30T00:00:00Z", "expires": None, "updated": None},
        "remarks": [],
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
        "autnums": [
            {"handle": "AS15169", "name": "GOOGLE", "start_autnum": 15169, "end_autnum": 15169},
            {"handle": "AS36040", "name": "YOUTUBE", "start_autnum": 36040, "end_autnum": 36040},
        ],
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
            "cache_expires": "2026-02-25T00:00:00Z",
        },
    }

    result = EntityResponse.model_validate(data)

    assert result.handle == "GOGL"
    assert result.name == "Google LLC"
    assert result.entities.abuse is not None
    assert result.entities.abuse.email == "network-abuse@google.com"
    assert len(result.autnums) == 2
    assert result.autnums[0].handle == "AS15169"
    assert result.autnums[1].name == "YOUTUBE"
    assert result.networks[0].cidr == ["8.8.8.0/24"]
    assert result.public_ids[0].type == "ARIN OrgID"


def test_model_dump_roundtrip():
    data = {
        "handle": "AS15169",
        "name": "GOOGLE",
        "type": None,
        "start_autnum": 15169,
        "end_autnum": 15169,
        "status": ["active"],
        "dates": {"registered": "2000-03-30T00:00:00Z", "expires": None, "updated": None},
        "entities": {},
        "remarks": [],
        "port43": "whois.arin.net",
        "meta": {
            "rdap_server": "https://rdap.arin.net/registry/",
            "raw_rdap_url": "https://rdap.arin.net/registry/autnum/15169",
            "cached": False,
            "cache_expires": "2026-02-25T00:00:00Z",
        },
    }

    original = AsnResponse.model_validate(data)
    dumped = original.model_dump()
    restored = AsnResponse.model_validate(dumped)

    assert original == restored
    assert restored.handle == "AS15169"


def test_dates_parsed_properties():
    from datetime import datetime, timezone

    dates = Dates.model_validate(
        {"registered": "2020-01-01T00:00:00Z", "expires": "2028-09-14T04:00:00Z", "updated": None}
    )

    assert dates.registered_at == datetime(2020, 1, 1, tzinfo=timezone.utc)
    assert dates.expires_at == datetime(2028, 9, 14, 4, 0, 0, tzinfo=timezone.utc)
    assert dates.updated_at is None
    assert isinstance(dates.expires_in_days, int)
    assert dates.expires_in_days > 0


def test_dates_null_returns_none():
    dates = Dates.model_validate({"registered": None, "expires": None, "updated": None})

    assert dates.registered_at is None
    assert dates.expires_at is None
    assert dates.updated_at is None
    assert dates.expires_in_days is None


def test_dates_invalid_string_returns_none():
    dates = Dates.model_validate({"registered": "not-a-date", "expires": "garbage", "updated": None})

    assert dates.registered_at is None
    assert dates.expires_at is None


def test_bulk_domain_response_parses():
    data = {
        "results": [
            {
                "domain": "google.com",
                "status": "success",
                "data": {
                    "domain": "google.com",
                    "unicode_name": None,
                    "handle": None,
                    "status": ["active"],
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
                    "meta": {
                        "rdap_server": "https://rdap.verisign.com/com/v1/",
                        "raw_rdap_url": "https://rdap.verisign.com/com/v1/domain/google.com",
                        "cached": False,
                        "cache_expires": "2026-02-25T00:00:00Z",
                    },
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

    result = BulkDomainResponse.model_validate(data)

    assert result.summary.total == 2
    assert result.summary.successful == 1
    assert result.summary.failed == 1
    assert result.results[0].status == "success"
    assert result.results[0].data is not None
    assert result.results[0].data.registrar.name == "MarkMonitor Inc."
    assert result.results[0].data.meta.cached is False
    assert result.results[1].status == "error"
    assert result.results[1].error == "invalid_domain"
    assert result.results[1].data is None
