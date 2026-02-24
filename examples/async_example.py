"""Async lookups with AsyncRdapApi."""

import asyncio

from rdapapi import AsyncRdapApi


async def main():
    async with AsyncRdapApi("your-api-key") as api:
        # Run multiple lookups concurrently
        domain, ip, asn = await asyncio.gather(
            api.domain("google.com"),
            api.ip("8.8.8.8"),
            api.asn(15169),
        )

        print(f"Domain: {domain.domain} (registrar: {domain.registrar.name})")
        print(f"IP: {ip.name} ({', '.join(ip.cidr)})")
        print(f"ASN: {asn.handle} ({asn.name})")


asyncio.run(main())
