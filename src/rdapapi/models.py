"""Pydantic models for RDAP API responses."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

__all__ = [
    "AsnResponse",
    "BulkDomainResponse",
    "BulkDomainResult",
    "BulkDomainSummary",
    "Contact",
    "Dates",
    "DomainResponse",
    "Entities",
    "EntityAutnum",
    "EntityNetwork",
    "EntityResponse",
    "FieldAvailability",
    "IpAddresses",
    "IpResponse",
    "Meta",
    "NameserverResponse",
    "PingResponse",
    "PublicId",
    "Redaction",
    "RedactionMethod",
    "Registrar",
    "Remark",
    "TldEntry",
    "TldListMeta",
    "TldListResponse",
    "TldMeta",
    "TldResponse",
    "TldThresholds",
]

RedactionMethod = str
"""How a value was withheld: ``removal``, ``emptyValue``, ``partialValue`` or
``replacementValue``. A server may send something else, which is passed through
unchanged, so this stays a plain :class:`str` rather than a closed enum."""


class Meta(BaseModel):
    """Where the answer came from, and how it was served.

    Only ``source`` is always sent. Every other field can be missing: ``rdap_server``
    and ``raw_rdap_url`` are absent when ``source`` is ``"whois"``, and a failed bulk
    entry carries ``server`` and ``source`` alone. Use ``"cached" in meta.model_fields_set``
    to tell a field the server omitted from one it sent as ``null``.
    """

    server: Optional[str] = None
    source: str
    rdap_server: Optional[str] = None
    raw_rdap_url: Optional[str] = None
    cached: Optional[bool] = None
    cache_expires: Optional[str] = None
    followed: Optional[bool] = None
    registrar_rdap_server: Optional[str] = None
    follow_error: Optional[str] = None


class Redaction(BaseModel):
    """What the upstream server declared it withheld, and by what method.

    Mirrors the shape of the record it describes, so a claim about
    ``entities.registrant.name`` sits at ``redacted.entities["registrant"]["name"]``.
    The whole object is absent — ``redacted`` is ``None`` — when the server declared
    nothing, which is not evidence that nothing was withheld.
    """

    handle: Optional[RedactionMethod] = None
    registrar: Dict[str, RedactionMethod] = Field(default_factory=dict)
    entities: Dict[str, Dict[str, RedactionMethod]] = Field(default_factory=dict)


class Dates(BaseModel):
    """Registration dates."""

    registered: Optional[str] = None
    expires: Optional[str] = None
    updated: Optional[str] = None

    @staticmethod
    def _parse(value: Optional[str]) -> Optional[datetime]:
        if value is None:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    @property
    def registered_at(self) -> Optional[datetime]:
        """Parse ``registered`` into a timezone-aware :class:`~datetime.datetime`."""
        return self._parse(self.registered)

    @property
    def expires_at(self) -> Optional[datetime]:
        """Parse ``expires`` into a timezone-aware :class:`~datetime.datetime`."""
        return self._parse(self.expires)

    @property
    def updated_at(self) -> Optional[datetime]:
        """Parse ``updated`` into a timezone-aware :class:`~datetime.datetime`."""
        return self._parse(self.updated)

    @property
    def expires_in_days(self) -> Optional[int]:
        """Days until expiration, or ``None`` if no expiry date is available."""
        dt = self.expires_at
        if dt is None:
            return None
        return (dt - datetime.now(timezone.utc)).days


class Registrar(BaseModel):
    """Domain registrar information."""

    name: Optional[str] = None
    iana_id: Optional[str] = None
    abuse_email: Optional[str] = None
    abuse_phone: Optional[str] = None
    url: Optional[str] = None


class Contact(BaseModel):
    """Contact entity information."""

    handle: Optional[str] = None
    name: Optional[str] = None
    organization: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    contact_url: Optional[str] = None
    country_code: Optional[str] = None


class Entities(BaseModel):
    """Contact entities keyed by role."""

    registrant: Optional[Contact] = None
    administrative: Optional[Contact] = None
    technical: Optional[Contact] = None
    billing: Optional[Contact] = None
    abuse: Optional[Contact] = None


class Remark(BaseModel):
    """Remark from the registry."""

    title: Optional[str] = None
    description: str


class DomainResponse(BaseModel):
    """Response from a domain lookup.

    ``dnssec`` is ``None`` where the registry publishes no DNSSEC status, as ``.tr``,
    ``.gg`` and ``.nc`` do not — distinct from ``False``, an unsigned delegation.
    """

    domain: str
    unicode_name: Optional[str] = None
    handle: Optional[str] = None
    status: List[str] = Field(default_factory=list)
    registrar: Registrar
    dates: Dates
    nameservers: List[str] = Field(default_factory=list)
    dnssec: Optional[bool] = None
    entities: Entities = Field(default_factory=Entities)
    redacted: Optional[Redaction] = None
    meta: Meta


class IpAddresses(BaseModel):
    """IP addresses for a nameserver."""

    v4: List[str] = Field(default_factory=list)
    v6: List[str] = Field(default_factory=list)


class IpResponse(BaseModel):
    """Response from an IP address lookup.

    ``geofeed`` is the RFC 8805 URL this network publishes, as published: never
    fetched, and never inherited from a parent network.
    """

    handle: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    start_address: Optional[str] = None
    end_address: Optional[str] = None
    ip_version: Optional[str] = None
    parent_handle: Optional[str] = None
    country: Optional[str] = None
    status: List[str] = Field(default_factory=list)
    dates: Dates
    entities: Entities = Field(default_factory=Entities)
    cidr: List[str] = Field(default_factory=list)
    geofeed: Optional[str] = None
    remarks: List[Remark] = Field(default_factory=list)
    port43: Optional[str] = None
    redacted: Optional[Redaction] = None
    meta: Meta


class AsnResponse(BaseModel):
    """Response from an ASN lookup."""

    handle: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    start_autnum: Optional[int] = None
    end_autnum: Optional[int] = None
    country: Optional[str] = None
    status: List[str] = Field(default_factory=list)
    dates: Dates
    entities: Entities = Field(default_factory=Entities)
    remarks: List[Remark] = Field(default_factory=list)
    port43: Optional[str] = None
    redacted: Optional[Redaction] = None
    meta: Meta


class NameserverResponse(BaseModel):
    """Response from a nameserver lookup."""

    ldh_name: str
    unicode_name: Optional[str] = None
    handle: Optional[str] = None
    ip_addresses: IpAddresses = Field(default_factory=IpAddresses)
    status: List[str] = Field(default_factory=list)
    dates: Dates
    entities: Entities = Field(default_factory=Entities)
    redacted: Optional[Redaction] = None
    meta: Meta


class PublicId(BaseModel):
    """Public identifier (e.g. ARIN OrgID, IANA Registrar ID)."""

    type: Optional[str] = None
    identifier: Optional[str] = None


class EntityAutnum(BaseModel):
    """Autonomous system number owned by an entity."""

    handle: Optional[str] = None
    name: Optional[str] = None
    start_autnum: Optional[int] = None
    end_autnum: Optional[int] = None


class EntityNetwork(BaseModel):
    """IP network block owned by an entity."""

    handle: Optional[str] = None
    name: Optional[str] = None
    start_address: Optional[str] = None
    end_address: Optional[str] = None
    ip_version: Optional[str] = None
    cidr: List[str] = Field(default_factory=list)


class BulkDomainResult(BaseModel):
    """A single result within a bulk domain lookup response.

    When ``status`` is ``"success"``, ``data`` contains a full
    :class:`DomainResponse`.  When ``status`` is ``"error"``,
    ``error`` and ``message`` describe the failure.

    ``meta`` names the upstream that answered, or that was tried. A failed entry
    carries ``server`` and ``source`` alone, and one that failed before an upstream
    was chosen — ``invalid_domain`` does — carries no ``meta`` at all.
    """

    domain: str
    status: str
    data: Optional[DomainResponse] = None
    meta: Optional[Meta] = None
    error: Optional[str] = None
    message: Optional[str] = None


class BulkDomainSummary(BaseModel):
    """Summary counts for a bulk domain lookup."""

    total: int
    successful: int
    failed: int


class BulkDomainResponse(BaseModel):
    """Response from a bulk domain lookup."""

    results: List[BulkDomainResult]
    summary: BulkDomainSummary


class FieldAvailability(BaseModel):
    """How often each common domain field is populated in a TLD's RDAP responses.

    Each value is one of ``"always"``, ``"usually"``, ``"sometimes"``, or
    ``"never"``. See :class:`TldThresholds` for the percentage cutoffs.
    """

    registrar: str
    registered_at: str
    expires_at: str
    nameservers: str
    status: str


class TldEntry(BaseModel):
    """A single TLD entry from the ``/tlds`` catalog.

    ``protocol`` is ``"whois"`` for the ccTLDs IANA lists no RDAP server for. Those
    have no ``rdap_server_host`` or ``rdap_server_url``, and no ``field_availability``
    — it is measured from RDAP responses. Use ``server`` for the host that answers,
    whichever protocol it speaks.
    """

    tld: str
    protocol: str
    supported_since: str
    server: str
    rdap_server_host: Optional[str] = None
    rdap_server_url: Optional[str] = None
    field_availability: Optional[FieldAvailability] = None


class TldThresholds(BaseModel):
    """Percentage cutoffs used to pick each availability label."""

    always: float
    usually: float
    sometimes: float


class TldListMeta(BaseModel):
    """Metadata for a TLD list response."""

    computed_at: str
    count: int
    coverage: float
    thresholds: TldThresholds


class TldMeta(BaseModel):
    """Metadata for a single-TLD response."""

    computed_at: str
    thresholds: TldThresholds


class TldListResponse(BaseModel):
    """Response from ``GET /tlds``."""

    data: List[TldEntry]
    meta: TldListMeta
    etag: Optional[str] = None


class TldResponse(BaseModel):
    """Response from ``GET /tlds/{tld}``."""

    data: TldEntry
    meta: TldMeta
    etag: Optional[str] = None


class EntityResponse(BaseModel):
    """Response from an entity lookup."""

    handle: Optional[str] = None
    name: Optional[str] = None
    organization: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    contact_url: Optional[str] = None
    country_code: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    status: List[str] = Field(default_factory=list)
    dates: Dates
    remarks: List[Remark] = Field(default_factory=list)
    port43: Optional[str] = None
    public_ids: List[PublicId] = Field(default_factory=list)
    entities: Entities = Field(default_factory=Entities)
    autnums: List[EntityAutnum] = Field(default_factory=list)
    networks: List[EntityNetwork] = Field(default_factory=list)
    redacted: Optional[Redaction] = None
    meta: Meta


class PingResponse(BaseModel):
    """Response from the ``/ping`` health check."""

    status: str
