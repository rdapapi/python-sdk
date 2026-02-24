"""Pydantic models for RDAP API responses."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

__all__ = [
    "AsnResponse",
    "Contact",
    "Dates",
    "DomainResponse",
    "Entities",
    "EntityAutnum",
    "EntityNetwork",
    "EntityResponse",
    "IpAddresses",
    "IpResponse",
    "Meta",
    "NameserverResponse",
    "PublicId",
    "Registrar",
    "Remark",
]


class Meta(BaseModel):
    """Metadata about the RDAP lookup."""

    rdap_server: str
    raw_rdap_url: str
    cached: bool
    cache_expires: str
    followed: Optional[bool] = None
    registrar_rdap_server: Optional[str] = None
    follow_error: Optional[str] = None


class Dates(BaseModel):
    """Registration dates."""

    registered: Optional[str] = None
    expires: Optional[str] = None
    updated: Optional[str] = None


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
    """Response from a domain lookup."""

    domain: str
    unicode_name: Optional[str] = None
    handle: Optional[str] = None
    status: List[str] = Field(default_factory=list)
    registrar: Registrar
    dates: Dates
    nameservers: List[str] = Field(default_factory=list)
    dnssec: bool = False
    entities: Entities = Field(default_factory=Entities)
    meta: Meta


class IpAddresses(BaseModel):
    """IP addresses for a nameserver."""

    v4: List[str] = Field(default_factory=list)
    v6: List[str] = Field(default_factory=list)


class IpResponse(BaseModel):
    """Response from an IP address lookup."""

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
    remarks: List[Remark] = Field(default_factory=list)
    port43: Optional[str] = None
    meta: Meta


class AsnResponse(BaseModel):
    """Response from an ASN lookup."""

    handle: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    start_autnum: Optional[int] = None
    end_autnum: Optional[int] = None
    status: List[str] = Field(default_factory=list)
    dates: Dates
    entities: Entities = Field(default_factory=Entities)
    remarks: List[Remark] = Field(default_factory=list)
    port43: Optional[str] = None
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
    meta: Meta
