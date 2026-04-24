"""List the TLDs the RDAP API supports and their field availability."""

from rdapapi import RdapApi

api = RdapApi("your-api-key")

# Full catalog. Does not count against your monthly quota.
tlds = api.tlds()
print(f"{tlds.meta.count} TLDs supported, coverage {tlds.meta.coverage:.0%}")
print(f"Computed at {tlds.meta.computed_at}")
print()

for tld in tlds.data[:5]:
    availability = tld.field_availability
    if availability is None:
        print(f".{tld.tld} via {tld.rdap_server_host} (not enough data yet)")
    else:
        print(
            f".{tld.tld} via {tld.rdap_server_host}: "
            f"registrar={availability.registrar}, expires_at={availability.expires_at}"
        )

print()

# Skip the transfer when nothing has changed.
later = api.tlds(if_none_match=tlds.etag)
print("Changed" if later is not None else "No change since last poll")

# Look up a single TLD.
com = api.tld("com")
if com is not None:
    print(f"\n.com supported since {com.data.supported_since}")

api.close()
