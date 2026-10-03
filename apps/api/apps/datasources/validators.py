"""Outbound-host validation for data-source connections.

Connecting to a customer-chosen host is an SSRF-shaped risk. We reduce it by
rejecting obviously dangerous targets *by IP class*, using a pluggable resolver
so the rule can be tested deterministically:

- loopback
- link-local (includes the 169.254.169.254 cloud metadata endpoint)
- multicast / reserved / unspecified
- private ranges (RFC1918 / ULA) unless ``DATASOURCE_ALLOW_PRIVATE_NETWORKS``

Note (honest limitation): this is a *shape* check performed at creation and at
connect time. It does not defend against DNS rebinding between our check and the
connection. The AI service performs the authoritative, connect-time check. See
security/threat-model/ssrf.md.
"""
from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable

from django.conf import settings
from rest_framework import serializers

Resolver = Callable[[str], list[str]]

_METADATA_HOSTS = {"metadata.google.internal", "metadata.goog"}


def _default_resolver(host: str) -> list[str]:
    infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    return sorted({info[4][0] for info in infos})


def _private_networks_allowed() -> bool:
    return bool(getattr(settings, "DATASOURCE_ALLOW_PRIVATE_NETWORKS", False))


def classify_ip(ip: str, *, allow_private: bool) -> str:
    """Return 'ok' or a rejection reason for a single IP address."""
    address = ipaddress.ip_address(ip)
    if address.is_loopback:
        return "loopback addresses are not allowed"
    if address.is_link_local:
        return "link-local addresses (including cloud metadata) are not allowed"
    if address.is_multicast or address.is_reserved or address.is_unspecified:
        return "multicast/reserved addresses are not allowed"
    if address.is_private and not allow_private:
        return "private network addresses are disabled for this deployment"
    return "ok"


def validate_host(host: str, *, resolver: Resolver | None = None) -> None:
    """Raise a DRF validation error if `host` must not be connected to.

    Every address the hostname resolves to is checked, so a name that resolves to
    a forbidden address is rejected even if it also resolves to a permitted one.
    """
    host = (host or "").strip()
    if not host:
        raise serializers.ValidationError("Host is required.")
    if host in _METADATA_HOSTS:
        raise serializers.ValidationError("That host is not allowed.")
    if any(char in host for char in " /\t\r\n"):
        raise serializers.ValidationError("Host must not contain whitespace or slashes.")

    allow_private = _private_networks_allowed()
    resolve = resolver or _default_resolver

    try:
        addresses = [host] if _is_literal_ip(host) else resolve(host)
    except socket.gaierror as exc:
        raise serializers.ValidationError(
            "Host could not be resolved. Check the address and try again."
        ) from exc

    if not addresses:
        raise serializers.ValidationError("Host did not resolve to any address.")

    for ip in addresses:
        reason = classify_ip(ip, allow_private=allow_private)
        if reason != "ok":
            raise serializers.ValidationError(f"Host is not allowed: {reason}.")


def _is_literal_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def validate_port(port: int) -> None:
    if not (1 <= port <= 65535):
        raise serializers.ValidationError("Port must be between 1 and 65535.")


def assert_connection_config_allowed(config: dict, *, resolver: Resolver | None = None) -> None:
    """Re-validate a stored connection config immediately before use."""
    validate_host(config.get("host", ""), resolver=resolver)
    validate_port(int(config.get("port", 0)))
    if not config.get("database"):
        raise serializers.ValidationError("A database name is required.")
