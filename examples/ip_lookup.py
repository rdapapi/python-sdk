"""Look up IP address and ASN registration data via the RDAP API."""

from rdapapi import RdapApi

api = RdapApi("your-api-key")

# IP address lookup
ip = api.ip("8.8.8.8")
print(f"Network: {ip.name} ({ip.handle})")
print(f"Range: {ip.start_address} - {ip.end_address}")
print(f"CIDR: {', '.join(ip.cidr)}")
print(f"Version: {ip.ip_version}")
print()

# ASN lookup
asn = api.asn(15169)
print(f"ASN: {asn.handle}")
print(f"Name: {asn.name}")
print(f"Range: {asn.start_autnum} - {asn.end_autnum}")

api.close()
