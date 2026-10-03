"""Outbound host guard — the authoritative check before we connect out.

The API validates a host when a data source is created. This module performs the
check again at connect time, immediately before opening a socket, so a
later-changed DNS record or a direct internal call cannot bypass it.

Honest limitation: this is a resolve-then-connect check. A hostile DNS server
could return a benign address here and a sensitive one to the driver
(DNS rebinding). Mitigations are tracked in security/threat-model/ssrf.md.
"""
from __future__ import annotations

import ipaddress
import socket

_METADATA_HOSTS = {"metadata.google.internal", "metadata.goog"}


class HostNotAllowed(ValueError):
    """Raised when a target host must not be connected to."""


def _classify(ip: str, *, allow_private: bool) -> str | None:
    address = ipaddress.ip_address(ip)
    if address.is_loopback:
        return "loopback addresses are not allowed"
    if address.is_link_local:
        return "link-local addresses (including cloud metadata) are not allowed"
    if address.is_multicast or address.is_reserved or address.is_unspecified:
        return "multicast/reserved addresses are not allowed"
    if address.is_private and not allow_private:
        return "private network addresses are disabled for this deployment"
    return None


def assert_host_allowed(host: str, *, allow_private: bool = False,
                        resolver=None) -> list[str]:
    """Raise `HostNotAllowed` unless every resolved address is permitted."""
    host = (host or "").strip()
    if not host:
        raise HostNotAllowed("Host is required.")
    if host in _METADATA_HOSTS:
        raise HostNotAllowed("That host is not allowed.")
    if any(c in host for c in " /\t\r\n"):
        raise HostNotAllowed("Host must not contain whitespace or slashes.")

    resolve = resolver or _resolve
    try:
        addresses = [host] if _is_ip(host) else resolve(host)
    except socket.gaierror as exc:
        raise HostNotAllowed("Host could not be resolved.") from exc
    if not addresses:
        raise HostNotAllowed("Host did not resolve to any address.")

    for ip in addresses:
        reason = _classify(ip, allow_private=allow_private)
        if reason:
            raise HostNotAllowed(f"Host is not allowed: {reason}.")
    return addresses


def _resolve(host: str) -> list[str]:
    infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    return sorted({info[4][0] for info in infos})


def _is_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False
