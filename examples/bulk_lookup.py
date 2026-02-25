"""Look up multiple domains in a single bulk request (Pro/Business plans)."""

from rdapapi import RdapApi

api = RdapApi("your-api-key")

# Bulk lookup — up to 10 domains in one request
result = api.bulk_domains(
    ["google.com", "github.com", "invalid..com"],
    follow=True,
)

print(f"Total: {result.summary.total}, OK: {result.summary.successful}, Failed: {result.summary.failed}")

for r in result.results:
    if r.status == "success":
        print(f"  {r.data.domain}: registrar={r.data.registrar.name}, expires={r.data.dates.expires}")
    else:
        print(f"  {r.domain}: {r.error} — {r.message}")

api.close()
