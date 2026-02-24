"""Look up multiple domains in a loop."""

from rdapapi import NotFoundError, RdapApi

api = RdapApi("your-api-key")

domains = ["google.com", "github.com", "cloudflare.com", "nonexistent.example"]

for name in domains:
    try:
        result = api.domain(name)
        print(f"{result.domain}: registrar={result.registrar.name}, expires={result.dates.expires}")
    except NotFoundError:
        print(f"{name}: not found")

api.close()
