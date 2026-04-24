# RDAP API Python SDK

[![PyPI version](https://img.shields.io/pypi/v/rdapapi.svg)](https://pypi.org/project/rdapapi/)
[![Python versions](https://img.shields.io/pypi/pyversions/rdapapi.svg)](https://pypi.org/project/rdapapi/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Official Python SDK for the [RDAP API](https://rdapapi.io) — look up domains, IP addresses, ASNs, nameservers, and entities via the RDAP protocol.

## Installation

```bash
pip install rdapapi
```

## Quick start

```python
from rdapapi import RdapApi

api = RdapApi("your-api-key")

# Domain lookup
domain = api.domain("google.com")
print(domain.registrar.name)     # "MarkMonitor Inc."
print(domain.dates.expires)      # "2028-09-14T04:00:00Z"
print(domain.nameservers)        # ["ns1.google.com", ...]

# IP address lookup
ip = api.ip("8.8.8.8")
print(ip.name)                   # "GOGL"
print(ip.cidr)                   # ["8.8.8.0/24"]

# ASN lookup
asn = api.asn(15169)
print(asn.name)                  # "GOOGLE"

# Nameserver lookup
ns = api.nameserver("ns1.google.com")
print(ns.ip_addresses.v4)       # ["216.239.32.10"]

# Entity lookup
entity = api.entity("GOGL")
print(entity.name)               # "Google LLC"
print(entity.autnums[0].handle) # "AS15169"

api.close()
```

## Bulk domain lookups

Look up multiple domains in a single request (Pro and Business plans). Up to 10 domains per call, with concurrent upstream fetches:

```python
result = api.bulk_domains(["google.com", "github.com", "invalid..com"], follow=True)

print(result.summary)  # total=3, successful=2, failed=1

for r in result.results:
    if r.status == "success":
        print(f"{r.data.domain}: {r.data.registrar.name}")
    else:
        print(f"{r.domain}: {r.error}")
```

Each domain counts as one request toward your monthly quota. Starter plans receive a `SubscriptionRequiredError` (403).

## Registrar follow-through

For thin registries like `.com` and `.net`, the registry only returns basic registrar info. Use `follow=True` to follow the registrar's RDAP link and get richer contact data:

```python
domain = api.domain("google.com", follow=True)
print(domain.entities.registrant.organization)  # "Google LLC"
print(domain.entities.registrant.email)         # "registrant@google.com"
```

## Error handling

```python
from rdapapi import RdapApi, NotFoundError, NotSupportedError, RateLimitError, AuthenticationError

api = RdapApi("your-api-key")

try:
    domain = api.domain("example.nope")
except NotSupportedError:
    print("The TLD is not covered by RDAP.")
except NotFoundError:
    print("The domain is not registered.")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except AuthenticationError:
    print("Invalid API key")
```

`NotSupportedError` is a subclass of `NotFoundError`, so catching `NotFoundError` still handles both cases. All exceptions inherit from `RdapApiError` and include `status_code`, `error`, and `message` attributes.

| Exception | HTTP Status | When |
|-----------|------------|------|
| `ValidationError` | 400 | Invalid input format |
| `AuthenticationError` | 401 | Missing or invalid API key |
| `SubscriptionRequiredError` | 403 | No active subscription |
| `NotFoundError` | 404 | Namespace is covered but no record exists |
| `NotSupportedError` | 404 | Namespace (TLD, IP range, ASN range) is not covered by RDAP |
| `RateLimitError` | 429 | Rate limit or quota exceeded |
| `UpstreamError` | 502 | Upstream RDAP server error |
| `TemporarilyUnavailableError` | 503 | Domain data temporarily unavailable |

## Supported TLDs catalog

List every TLD the API can resolve, with the date support was added and a qualitative summary of which fields the registry's RDAP server populates. Does not count against your monthly quota.

```python
tlds = api.tlds()
print(f"{tlds.meta.count} TLDs, coverage {tlds.meta.coverage:.0%}")

for tld in tlds.data:
    availability = tld.field_availability
    if availability is not None:
        print(f"{tld.tld}: expires_at={availability.expires_at}")
```

Filter to recent additions or to a single registry:

```python
recent = api.tlds(since="2026-04-01T00:00:00Z")
verisign = api.tlds(server="rdap.verisign.com")
```

Pass back the previous `etag` to skip the transfer when nothing has changed:

```python
first = api.tlds()
later = api.tlds(if_none_match=first.etag)
if later is None:
    print("No change since last poll")
```

Look up a single TLD:

```python
com = api.tld("com")
print(com.data.rdap_server_host)  # "rdap.verisign.com"
```

## Async support

```python
import asyncio
from rdapapi import AsyncRdapApi

async def main():
    async with AsyncRdapApi("your-api-key") as api:
        domain, ip, asn = await asyncio.gather(
            api.domain("google.com"),
            api.ip("8.8.8.8"),
            api.asn(15169),
        )
        print(f"{domain.domain}: {domain.registrar.name}")

asyncio.run(main())
```

## Serialization

All response objects are [Pydantic](https://docs.pydantic.dev/) models with full type hints:

```python
domain = api.domain("google.com")

# Convert to dict
data = domain.model_dump()

# Convert to JSON string
json_str = domain.model_dump_json()
```

## Configuration

```python
api = RdapApi(
    "your-api-key",
    base_url="https://rdapapi.io/api/v1",  # default
    timeout=30,                              # seconds, default
)
```

## Links

- [API Documentation](https://rdapapi.io/docs)
- [Get an API Key](https://rdapapi.io/register)
- [OpenAPI Spec](https://rdapapi.io/openapi.yaml)
- [Pricing](https://rdapapi.io/pricing)

## Development

Set up pre-commit hooks (runs lint + tests before each commit):

```bash
git config core.hooksPath .githooks
```

## License

MIT
