"""Look up domain registration data via the RDAP API."""

from rdapapi import RdapApi

api = RdapApi("your-api-key")

# Basic domain lookup
domain = api.domain("google.com")
print(f"Domain: {domain.domain}")
print(f"Registrar: {domain.registrar.name}")
print(f"Registered: {domain.dates.registered}")
print(f"Expires: {domain.dates.expires}")
print(f"Nameservers: {', '.join(domain.nameservers)}")
print(f"DNSSEC: {domain.dnssec}")  # None where the registry publishes no status
print(f"Answered over {domain.meta.source} by {domain.meta.server}")
print()

# Follow registrar link for richer contact data (thin registries like .com)
domain = api.domain("google.com", follow=True)
if domain.entities.registrant:
    print(f"Registrant: {domain.entities.registrant.organization}")
    print(f"Email: {domain.entities.registrant.email}")
print()

# TLDs with no RDAP server are answered over WHOIS; pass whois=False to refuse that.
domain = api.domain("google.it")
print(f"{domain.domain} answered over {domain.meta.source}")

# What the server declared it withheld, when it declares anything at all.
domain = api.domain("google.co.uk")
if domain.redacted is not None:
    for role, fields in domain.redacted.entities.items():
        for field, method in fields.items():
            print(f"Redacted: {role}.{field} ({method})")

api.close()
