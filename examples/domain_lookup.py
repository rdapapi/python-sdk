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
print(f"DNSSEC: {domain.dnssec}")
print()

# Follow registrar link for richer contact data (thin registries like .com)
domain = api.domain("google.com", follow=True)
if domain.entities.registrant:
    print(f"Registrant: {domain.entities.registrant.organization}")
    print(f"Email: {domain.entities.registrant.email}")

api.close()
