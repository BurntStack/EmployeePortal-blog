"""Bounded HEAD requests with IP pinning: never connect to internal addresses."""
import http.client
import ipaddress
import socket
import ssl
from urllib.parse import urlsplit, urljoin
from concurrent.futures import ThreadPoolExecutor

from django.core.cache import cache
from .editorial import quality


class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address, port):
        super().__init__(host, port=port, timeout=3, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        self.sock = self._context.wrap_socket(socket.create_connection((self.address, self.port), timeout=self.timeout), server_hostname=self.host)


def check_url(url):
    original = url
    try:
        for _ in range(4):
            parsed = urlsplit(url)
            if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
                return {"url": original, "state": "unchecked", "detail": "Unsupported URL"}
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            if port not in (80, 443):
                return {"url": original, "state": "unchecked", "detail": "Nonstandard port"}
            addresses = {info[4][0] for info in socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)}
            if not addresses or any(not ipaddress.ip_address(ip).is_global or (getattr(ipaddress.ip_address(ip), "ipv4_mapped", None) and not ipaddress.ip_address(ip).ipv4_mapped.is_global) for ip in addresses):
                return {"url": original, "state": "unchecked", "detail": "Private network address"}
            address = sorted(addresses)[0]
            connection = PinnedHTTPS(parsed.hostname, address, port) if parsed.scheme == "https" else http.client.HTTPConnection(address, port=port, timeout=3)
            try:
                connection.request("HEAD", (parsed.path or "/") + ("?" + parsed.query if parsed.query else ""), headers={"Host": parsed.netloc, "User-Agent": "BurntStack-LinkCheck/1.0"})
                response = connection.getresponse()
                code, location = response.status, response.getheader("Location")
            finally:
                connection.close()
            if code in (301, 302, 303, 307, 308) and location:
                url = urljoin(url, location)
                continue
            return {"url": original, "status": code, "state": "broken" if code in (404, 410) else "ok" if 200 <= code < 400 else "unchecked", "detail": f"HTTP {code}"}
        return {"url": original, "state": "unchecked", "detail": "Too many redirects"}
    except (OSError, ValueError, http.client.HTTPException):
        return {"url": original, "state": "unchecked", "detail": "Could not verify; check manually"}


def check_links(post):
    key = f"links:{post.id}:{post.version}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    links = [url for url in quality(post)["links"] if url.startswith(("https://", "http://"))]
    with ThreadPoolExecutor(max_workers=5) as pool:
        result = {"results": list(pool.map(check_url, links[:20])), "skipped": max(0, len(links) - 20)}
    cache.set(key, result, 300)
    return result
