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

## Registrar follow-through

For thin registries like `.com` and `.net`, the registry only returns basic registrar info. Use `follow=True` to follow the registrar's RDAP link and get richer contact data:

```python
domain = api.domain("google.com", follow=True)
print(domain.entities.registrant.organization)  # "Google LLC"
print(domain.entities.registrant.email)         # "registrant@google.com"
```

## Error handling

```python
from rdapapi import RdapApi, NotFoundError, RateLimitError, AuthenticationError

api = RdapApi("your-api-key")

try:
    domain = api.domain("nonexistent.example")
except NotFoundError:
    print("Domain not found")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except AuthenticationError:
    print("Invalid API key")
```

All exceptions inherit from `RdapApiError` and include `status_code`, `error`, and `message` attributes.

| Exception | HTTP Status | When |
|-----------|------------|------|
| `ValidationError` | 400 | Invalid input format |
| `AuthenticationError` | 401 | Missing or invalid API key |
| `SubscriptionRequiredError` | 403 | No active subscription |
| `NotFoundError` | 404 | No RDAP data found |
| `RateLimitError` | 429 | Rate limit or quota exceeded |
| `UpstreamError` | 502 | Upstream RDAP server error |

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

## License

MIT
