"""Production canary — probe the live API through the SDK's own public API.

CI replays frozen fixtures, so it can prove the SDK is self-consistent but never
that the API moved underneath it. This calls production and fails when the live
contract stops matching what the models accept.

Deliberately outside ``tests/``, so pytest and its coverage gate never collect it.

Run it locally with the key in the environment::

    RDAPAPI_API_KEY=... python canary.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from typing import Awaitable, Callable, List, TypeVar

import httpx
from pydantic import ValidationError as ModelValidationError

from rdapapi import AsyncRdapApi, RdapApi, ServerError

T = TypeVar("T")

RETRY_BACKOFF_SECONDS = 5


class ProbeFailure(Exception):
    """A live response no longer matches what the SDK models."""


def check(passed: bool, message: str) -> None:
    """Fail the probe unless ``passed``, naming what was expected and what arrived."""
    if not passed:
        raise ProbeFailure(message)


def retrying(call: Callable[[], T]) -> T:
    """Call once more after a transport error or a 5xx.

    Registries go transiently down; a contract assertion is never retried, because
    a field that is wrong stays wrong.
    """
    try:
        return call()
    except (httpx.TransportError, ServerError) as exc:
        print(f"  transient failure, retrying once in {RETRY_BACKOFF_SECONDS}s: {exc!r}")
        time.sleep(RETRY_BACKOFF_SECONDS)
        return call()


async def retrying_async(call: Callable[[], Awaitable[T]]) -> T:
    """Async twin of :func:`retrying`."""
    try:
        return await call()
    except (httpx.TransportError, ServerError) as exc:
        print(f"  transient failure, retrying once in {RETRY_BACKOFF_SECONDS}s: {exc!r}")
        await asyncio.sleep(RETRY_BACKOFF_SECONDS)
        return await call()


def probe_ping(api: RdapApi) -> None:
    """1 — the API answers at all. Costs no quota."""
    ping = retrying(api.ping)
    check(ping.status == "ok", f"expected ping status 'ok', got {ping.status!r}")


def probe_rdap_domain(api: RdapApi) -> None:
    """2 — google.com with follow: an RDAP answer carrying registrar-level detail."""
    domain = retrying(lambda: api.domain("google.com", follow=True))

    check(
        domain.meta.source == "rdap",
        f"expected meta.source 'rdap' for google.com, got {domain.meta.source!r}",
    )
    check(
        bool(domain.meta.server),
        f"expected a non-empty meta.server for google.com, got {domain.meta.server!r}",
    )
    check(
        bool(domain.registrar.name),
        f"expected a non-empty registrar name for google.com, got {domain.registrar.name!r}",
    )

    roles = [role for role, contact in domain.entities.model_dump().items() if contact is not None]
    check(bool(roles), "expected at least one entity for google.com with follow=True, got none")


async def probe_whois_domain(api: AsyncRdapApi) -> None:
    """3 — google.it, answered over WHOIS, parses with no RDAP server in ``meta``.

    This is the shape that crashed 0.5.0 in production: ``Meta.rdap_server`` was
    required, and a WHOIS answer sends neither it nor ``raw_rdap_url``. Both must
    stay optional, so the model has to accept the response before anything else
    here can be asserted.
    """
    try:
        domain = await retrying_async(lambda: api.domain("google.it"))
    except ModelValidationError as exc:
        raise ProbeFailure(
            "the 0.5.0 production crash is back: google.it is answered over WHOIS, which sends no "
            "meta.rdap_server and no meta.raw_rdap_url, and the model rejected the response instead "
            f"of accepting both as absent — pydantic said: {exc}"
        ) from exc

    check(
        domain.meta.source == "whois",
        f"expected meta.source 'whois' for google.it, got {domain.meta.source!r}",
    )
    check(
        domain.meta.server == "whois.nic.it",
        f"expected meta.server 'whois.nic.it' for google.it, got {domain.meta.server!r}",
    )
    check(
        domain.meta.rdap_server is None,
        f"expected meta.rdap_server absent or null on a WHOIS answer, got {domain.meta.rdap_server!r}",
    )
    check(
        domain.meta.raw_rdap_url is None,
        f"expected meta.raw_rdap_url absent or null on a WHOIS answer, got {domain.meta.raw_rdap_url!r}",
    )


async def probe_ip_geofeed(api: AsyncRdapApi) -> None:
    """4 — 45.83.220.1 publishes an RFC 8805 geofeed URL.

    The geofeed is the network holder's to publish; if this fails, check that they
    still publish one before suspecting the SDK.
    """
    ip = await retrying_async(lambda: api.ip("45.83.220.1"))

    check(
        bool(ip.geofeed),
        f"expected a non-empty geofeed for 45.83.220.1, got {ip.geofeed!r}",
    )


def probe_whois_tld(api: RdapApi) -> None:
    """5 — .it is catalogued as WHOIS-served, with the deprecated RDAP fields null."""
    response = retrying(lambda: api.tld("it"))
    check(response is not None, "expected a body for tld 'it', got HTTP 304 without an If-None-Match")

    entry = response.data
    check(
        entry.protocol == "whois",
        f"expected protocol 'whois' for tld 'it', got {entry.protocol!r}",
    )
    check(
        bool(entry.server),
        f"expected a non-empty server for tld 'it', got {entry.server!r}",
    )
    check(
        entry.rdap_server_host is None,
        f"expected rdap_server_host null for the WHOIS-served tld 'it', got {entry.rdap_server_host!r}",
    )
    check(
        entry.rdap_server_url is None,
        f"expected rdap_server_url null for the WHOIS-served tld 'it', got {entry.rdap_server_url!r}",
    )


def run(name: str, probe: Callable[[], None], failures: List[str]) -> None:
    """Run one probe, recording its failure rather than stopping the run."""
    print(f"probe {name}")
    try:
        probe()
    except Exception as exc:
        failures.append(f"{name}: {exc}")
        print(f"  FAIL — {exc}")
    else:
        print("  ok")


async def run_async(name: str, probe: Callable[[], Awaitable[None]], failures: List[str]) -> None:
    """Async twin of :func:`run`."""
    print(f"probe {name}")
    try:
        await probe()
    except Exception as exc:
        failures.append(f"{name}: {exc}")
        print(f"  FAIL — {exc}")
    else:
        print("  ok")


async def async_probes(api_key: str, failures: List[str]) -> None:
    """The probes driven through the async client, which drifts from the sync one."""
    async with AsyncRdapApi(api_key) as api:
        await run_async("3 whois domain (async)", lambda: probe_whois_domain(api), failures)
        await run_async("4 ip geofeed (async)", lambda: probe_ip_geofeed(api), failures)


def main() -> int:
    api_key = os.environ.get("RDAPAPI_API_KEY", "")
    if not api_key:
        print("RDAPAPI_API_KEY is not set")
        return 1

    failures: List[str] = []

    with RdapApi(api_key) as api:
        run("1 ping (sync)", lambda: probe_ping(api), failures)
        run("2 rdap domain (sync)", lambda: probe_rdap_domain(api), failures)
        run("5 whois tld (sync)", lambda: probe_whois_tld(api), failures)

    asyncio.run(async_probes(api_key, failures))

    if failures:
        print(f"\n{len(failures)} probe(s) failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print("\nAll probes passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
