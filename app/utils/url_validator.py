"""SSRF protection — validate external URLs before fetching."""
import ipaddress
import socket
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def validate_external_url(url: str) -> bool:
    """Validate that a URL is safe to fetch (no SSRF).

    Rejects private IPs, localhost, link-local, cloud metadata,
    and non-http(s) schemes. Resolves hostname to check actual IP.

    Returns True if safe, False if blocked.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            logger.warning(f"[SSRF] Blocked non-http scheme: {parsed.scheme}")
            return False

        hostname = parsed.hostname
        if not hostname:
            logger.warning("[SSRF] Blocked URL with no hostname")
            return False

        try:
            addr_infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror:
            logger.warning(f"[SSRF] Could not resolve hostname: {hostname}")
            return False

        for addr_info in addr_infos:
            ip_str = addr_info[4][0]
            try:
                ip = ipaddress.ip_address(ip_str)
            except ValueError:
                continue

            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                logger.warning(f"[SSRF] Blocked private/reserved IP {ip} for host {hostname}")
                return False

        return True
    except Exception as e:
        logger.warning(f"[SSRF] URL validation error: {e}")
        return False
