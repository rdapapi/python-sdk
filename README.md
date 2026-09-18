# RDAP API Python SDK

[![PyPI version](https://img.shields.io/pypi/v/rdapapi.svg)](https://pypi.org/project/rdapapi/)
[![Python versions](https://img.shields.io/pypi/pyversions/rdapapi.svg)](https://pypi.org/project/rdapapi/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Official Python SDK for the [RDAP API](https://rdapapi.io) — look up domains, IP addresses, ASNs, nameservers, and entities over RDAP, with a WHOIS fallback for the TLDs RDAP does not cover.

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
print(domain.dnssec)             # False, or None where the registry publishes no status
print(domain.meta.source)        # "rdap", or "whois" for a TLD with no RDAP server

# IP address lookup — pass an address or a CIDR block
ip = api.ip("8.8.8.8")
print(ip.name)                   # "GOGL"
print(ip.cidr)                   # ["8.8.8.0/24"]
print(ip.geofeed)                # RFC 8805 geofeed URL, or None

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

`follow` and `whois` apply to every domain in the request. Each domain counts as one request toward your monthly quota. Starter plans receive a `PlanUpgradeRequiredError` (403), a subclass of `SubscriptionRequiredError`.

## Registrar follow-through

For thin registries like `.com` and `.net`, the registry only returns basic registrar info. Use `follow=True` to follow the registrar's RDAP link and get richer contact data:

```python
domain = api.domain("google.com", follow=True)
print(domain.entities.registrant.organization)  # "Google LLC"
print(domain.entities.registrant.email)         # "registrant@google.com"
```

## WHOIS fallback

For the ccTLDs IANA lists no RDAP server for, the answer is read from the registry's WHOIS
server and returned in the same shape. `meta.source` says which protocol answered, and
`meta.server` names the host:

```python
domain = api.domain("google.it")
print(domain.meta.source)   # "whois"
print(domain.meta.server)   # "whois.nic.it"
```

A WHOIS registry publishes fewer fields — several give no dates, some no registrar — and
anything it withholds is `None` rather than inferred. `meta.rdap_server` and
`meta.raw_rdap_url` are absent, since WHOIS has no URL form.

Pass `whois=False` to refuse the fallback, so such a TLD raises `NotSupportedError`
instead:

```python
domain = api.domain("google.it", whois=False)  # raises NotSupportedError
```

## Declared redactions

`redacted` carries what the upstream server *declared* it withheld, mirroring the shape of
the record, so a claim about `entities.registrant.name` sits at
`redacted.entities["registrant"]["name"]`. It is `None` when the server declared nothing,
which is not evidence that nothing was withheld:

```python
domain = api.domain("google.co.uk")

if domain.redacted is not None:
    for role, fields in domain.redacted.entities.items():
        for field, method in fields.items():
            print(f"{role}.{field} withheld by {method}")
    # registrant.email withheld by replacementValue
```

The method is one of `removal`, `emptyValue`, `partialValue` or `replacementValue`. A
server may send something else, which is passed through unchanged, so it stays a plain
`str`.

## Health check

```python
print(api.ping().status)  # "ok"
```

Costs no quota. The endpoint itself answers unauthenticated callers, but the SDK is
an authenticated client: `RdapApi` rejects an empty key, so `ping()` checks that the
API answers *you*.

## Error handling

```python
from rdapapi import (
    RdapApi,
    AuthenticationError,
    NotFoundError,
    NotSupportedError,
    RateLimitError,
    SubscriptionRequiredError,
)

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
except SubscriptionRequiredError as e:
    if e.error == "forbidden":
        print("This IP is temporarily blocked. Retry later.")
    else:
        print("Subscribe at https://rdapapi.io/pricing")
```

`NotSupportedError` is a subclass of `NotFoundError`, and `PlanUpgradeRequiredError` of
`SubscriptionRequiredError`, so catching the parent still handles both cases. All
exceptions inherit from `RdapApiError` and include `status_code`, `error`, `message` and
`retry_after` attributes. Branch on `error`, the machine-readable code — never on
`message`, and never on the endpoint: any code can answer any endpoint.

| Exception | HTTP Status | `error` | When |
|-----------|------------|---------|------|
| `ValidationError` | 400 | `invalid_domain`, `invalid_ip`, `invalid_asn`, `invalid_nameserver`, `invalid_handle`, `invalid_prefix`, `invalid_since`, `bad_request` | Invalid input format |
| `AuthenticationError` | 401 | `unauthenticated` | Missing or invalid API key |
| `SubscriptionRequiredError` | 403 | `subscription_required` | No active subscription |
| `SubscriptionRequiredError` | 403 | `forbidden` | This IP is temporarily blocked. It lifts on its own, so retry later — API rate limits never cause it |
| `PlanUpgradeRequiredError` | 403 | `plan_upgrade_required` | Endpoint needs a higher plan |
| `NotFoundError` | 404 | `not_found` | Namespace is covered but no record exists |
| `NotSupportedError` | 404 | `not_supported` | Namespace (TLD, IP range, ASN range) is covered by neither RDAP nor the WHOIS fallback |
| `MethodNotAllowedError` | 405 | `method_not_allowed` | Wrong HTTP method for the endpoint |
| `PayloadTooLargeError` | 413 | `payload_too_large` | Request body too large |
| `RequestFailedError` | 422 | `request_failed` | Body failed validation; `errors` names the fields |
| `RateLimitError` | 429 | `rate_limit_exceeded`, `quota_exceeded`, `too_many_requests` | Rate limit or quota exceeded |
| `UpstreamError` | 502 | `lookup_failed`, `bad_gateway` | Upstream RDAP server error |
| `TemporarilyUnavailableError` | 503 | `temporarily_unavailable`, `service_unavailable` | Data temporarily unavailable |
| `GatewayTimeoutError` | 504 | `gateway_timeout` | Request did not complete in time |
| `ServerError` | 5xx | `server_error` | Any other server-side failure |

`UpstreamError`, `TemporarilyUnavailableError` and `GatewayTimeoutError` all inherit from
`ServerError`, so `except ServerError` covers the 5xx failures worth retrying after a
delay. An error body that is not JSON — a CDN edge page, say — surfaces the same way, with
`error` set to `"unknown_error"`.

One 403 is retryable and does not go through `ServerError`: `forbidden` is a temporary IP
block that lifts on its own. It shares `SubscriptionRequiredError` with
`subscription_required`, which is not retryable at all, so branch on `e.error` there
rather than showing every 403 a billing prompt.

`retry_after` is the number of seconds to wait. The `Retry-After` header wins, in either
form RFC 9110 allows — delta-seconds, or an HTTP-date, which arrives whenever an upstream
registry's own header is passed through — and the body's `retry_after` is the fallback. It
is `None` when neither gave an estimate.

A rejected request body names the fields it rejected:

```python
from rdapapi import RequestFailedError

try:
    api.bulk_domains(["a.com"] * 11)
except RequestFailedError as e:
    print(e.errors)  # {"domains": ["The domains field must not have more than 10 items."]}
```

## Supported TLDs catalog

List every TLD the API can resolve, with the date support was added and a qualitative summary of which fields the registry's RDAP server populates. Does not count against your monthly quota.

```python
tlds = api.tlds()
print(f"{tlds.meta.count} TLDs, coverage {tlds.meta.coverage:.0%}")

for tld in tlds.data:
    print(f"{tld.tld}: {tld.protocol} via {tld.server}")
    availability = tld.field_availability
    if availability is not None:
        print(f"  expires_at={availability.expires_at}")
```

`protocol` is `"whois"` for the ccTLDs IANA lists no RDAP server for. Those entries have no
`rdap_server_host` and no `rdap_server_url` — use `server` for the host that answers,
whichever protocol it speaks — and no `field_availability`, which is measured from RDAP
responses only.

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
print(com.data.server)  # "rdap.verisign.com"
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
