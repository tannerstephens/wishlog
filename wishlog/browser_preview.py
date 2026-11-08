"""Load a page in headless Chromium, for stores that refuse plain requests.

Playwright is optional: without it (or without its browser installed) this
module reports itself unavailable and link previews use plain requests only.

The browser makes its own connections (redirects, scripts, WebSockets) that
Playwright's request interception does not fully see, so instead every
connection is sent through a small local proxy. The proxy checks the real
address it connects to, the same way plain requests are checked, so pages
can't reach the server itself or the local network. HTTPS passes through the
proxy still encrypted.
"""

import os
import select
import socket
import socketserver
import threading
from urllib.parse import urlsplit

from .link_preview import LinkPreviewError, _public_connection

RENDER_TIMEOUT_MS = 12_000
SETTLE_TIMEOUT_MS = 3_000
MAX_HEAD_BYTES = 64 * 1024

# Resources not needed to read a page's details, skipped to load faster
SKIPPED_RESOURCES = {"image", "media", "font", "stylesheet"}


def available() -> bool:
    if os.environ.get("WISHLOG_BROWSER_PREVIEW", "").lower() in ("0", "false", "no", "off"):
        return False
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return False
    return True


# --- Guarding proxy --------------------------------------------------------


class _ProxyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        client = self.request
        client.settimeout(RENDER_TIMEOUT_MS / 1000)
        self.server.track(client)

        try:
            head, rest = self._read_head(client)
            request_line, _, header_block = head.partition(b"\r\n")
            method, target, version = request_line.decode("latin-1").split(" ", 2)
        except (OSError, ValueError):
            return

        try:
            if method.upper() == "CONNECT":
                host, _, port = target.rpartition(":")
                upstream = self._connect(host.strip("[]"), int(port))
                client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                if rest:
                    upstream.sendall(rest)
            else:
                # Plain HTTP: the proxy gets an absolute URL; send the
                # request on with just the path, as a server expects
                url = urlsplit(target)
                if url.scheme != "http" or not url.hostname:
                    raise ValueError("unsupported proxy request")
                upstream = self._connect(url.hostname, url.port or 80)
                path = url.path or "/"
                if url.query:
                    path += "?" + url.query
                headers = [
                    line
                    for line in header_block.split(b"\r\n")
                    if line and not line.lower().startswith((b"proxy-", b"connection:"))
                ]
                upstream.sendall(
                    f"{method} {path} {version}\r\n".encode("latin-1")
                    + b"\r\n".join(headers + [b"Connection: close"])
                    + b"\r\n\r\n"
                    + rest
                )
        except (LinkPreviewError, OSError, ValueError):
            try:
                client.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
            except OSError:
                pass
            return

        self._pipe(client, upstream)

    def _read_head(self, client):
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = client.recv(8192)
            if not chunk:
                raise ValueError("connection closed")
            data += chunk
            if len(data) > MAX_HEAD_BYTES:
                raise ValueError("request head too large")
        head, _, rest = data.partition(b"\r\n\r\n")
        return head, rest

    def _connect(self, host, port):
        # Resolves the name, refuses private addresses, and connects to the
        # very address it checked
        upstream = _public_connection((host, port), timeout=RENDER_TIMEOUT_MS / 1000)
        self.server.track(upstream)
        return upstream

    def _pipe(self, client, upstream):
        sockets = [client, upstream]
        other = {client: upstream, upstream: client}
        while not self.server.stopping.is_set():
            try:
                readable, _, _ = select.select(sockets, [], [], 0.5)
                for sock in readable:
                    data = sock.recv(65536)
                    if not data:
                        return
                    other[sock].sendall(data)
            except (OSError, ValueError):
                return


class _GuardProxy(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), _ProxyHandler)
        self.stopping = threading.Event()
        self._open = set()
        self._lock = threading.Lock()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_address[1]}"

    def track(self, sock):
        with self._lock:
            self._open.add(sock)

    def __enter__(self):
        threading.Thread(target=self.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.stopping.set()
        self.shutdown()
        self.server_close()
        with self._lock:
            for sock in self._open:
                try:
                    sock.close()
                except OSError:
                    pass


# --- Rendering -------------------------------------------------------------


def render(url: str) -> tuple[str, str, int]:
    """Return the page's HTML (after its scripts ran), final URL and status."""
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
    from playwright.sync_api import sync_playwright

    try:
        with _GuardProxy() as proxy, sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                # "<-loopback>" stops Chromium's built-in exception that would
                # otherwise send localhost straight past the proxy
                proxy={"server": proxy.url, "bypass": "<-loopback>"},
                args=[
                    # WebRTC can open UDP connections outside the proxy
                    "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
                    "--webrtc-ip-handling-policy=disable_non_proxied_udp",
                ],
            )
            try:
                # Service workers can make requests outside the page's view
                context = browser.new_context(service_workers="block")
                context.route(
                    "**/*",
                    lambda route: route.abort()
                    if route.request.resource_type in SKIPPED_RESOURCES
                    else route.continue_(),
                )
                page = context.new_page()

                response = page.goto(
                    url, wait_until="domcontentloaded", timeout=RENDER_TIMEOUT_MS
                )
                # Give scripts (and bot-check pages that reload) a moment
                try:
                    page.wait_for_load_state("networkidle", timeout=SETTLE_TIMEOUT_MS)
                except PlaywrightTimeout:
                    pass

                # A bot-check page may answer 403 and then reload itself into
                # the real page, so the caller judges by what the page holds
                status = response.status if response is not None else 0
                return page.content(), page.url, status
            finally:
                browser.close()
    except PlaywrightTimeout as e:
        raise LinkPreviewError("That page took too long to load") from e
    except PlaywrightError as e:
        raise LinkPreviewError("Could not load that page in the browser") from e
