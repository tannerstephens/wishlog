"""Fetch a product page and pull out its title, price and image.

Only the standard library is used. Pages are read from OpenGraph / Twitter
meta tags, schema.org JSON-LD and microdata, which most stores provide.

Every connection goes to a public IP address only: the host name is resolved
and checked at connect time (including after redirects), so a link can't make
the server talk to itself or to the local network.
"""

import gzip
import http.client
import ipaddress
import json
import re
import socket
import urllib.error
import urllib.request
import zlib
from base64 import b64encode
from dataclasses import dataclass
from email.message import Message
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse

TIMEOUT_SECONDS = 6
MAX_PAGE_BYTES = 3 * 1024 * 1024
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_TITLE_LENGTH = 200

# Many stores serve a bare or bot-check page to unknown clients
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}


class LinkPreviewError(Exception):
    pass


class FetchRefusedError(LinkPreviewError):
    """The website refused or failed the request; a real browser may do better."""


@dataclass
class LinkPreview:
    title: str | None = None
    cost: float | None = None
    image: str | None = None  # base64 encoded image bytes
    image_type: str | None = None
    image_name: str | None = None

    def to_dict(self):
        return {
            "title": self.title,
            "cost": self.cost,
            "image": self.image,
            "image_type": self.image_type,
            "image_name": self.image_name,
        }


# --- Safe fetching ---------------------------------------------------------


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def _public_connection(address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None, **_):
    """Like socket.create_connection, but only to public addresses.

    Connecting to the address that was checked (rather than resolving again)
    stops DNS rebinding from swapping in a private address afterwards.
    """
    host, port = address
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise LinkPreviewError("Could not find that website") from e

    public = [info for info in infos if _is_public(info[4][0])]
    if not public:
        raise LinkPreviewError("That address is not on the public internet")

    error = None
    for family, socktype, proto, _, sockaddr in public:
        sock = socket.socket(family, socktype, proto)
        try:
            if timeout is not socket._GLOBAL_DEFAULT_TIMEOUT:
                sock.settimeout(timeout)
            if source_address:
                sock.bind(source_address)
            sock.connect(sockaddr)
            return sock
        except OSError as e:
            error = e
            sock.close()
    raise error


class _PublicHTTPConnection(http.client.HTTPConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = _public_connection


class _PublicHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = _public_connection


class _PublicHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(_PublicHTTPConnection, req)


class _PublicHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_PublicHTTPSConnection, req, context=self._context)


class _HTTPOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    max_redirections = 5

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).scheme not in ("http", "https"):
            raise LinkPreviewError("The link redirected somewhere unsupported")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


# No ProxyHandler: a proxy would make the address checks meaningless
_opener = urllib.request.OpenerDirector()
for _handler in (
    _PublicHTTPHandler(),
    _PublicHTTPSHandler(),
    _HTTPOnlyRedirectHandler(),
    urllib.request.HTTPDefaultErrorHandler(),
    urllib.request.HTTPErrorProcessor(),
):
    _opener.add_handler(_handler)


def _fetch(url: str, max_bytes: int) -> tuple[bytes, Message, str]:
    """Return the body, headers and final URL (after redirects)."""
    request = urllib.request.Request(url, headers=HEADERS)
    try:
        with _opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read(max_bytes + 1)
            headers = response.headers
            final_url = response.geturl()
    except LinkPreviewError:
        raise
    except urllib.error.HTTPError as e:
        raise FetchRefusedError(f"The website responded with an error ({e.code})") from e
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as e:
        raise FetchRefusedError("Could not reach that website") from e

    encoding = (headers.get("Content-Encoding") or "").lower()
    try:
        if encoding == "gzip":
            body = gzip.decompress(body)
        elif encoding == "deflate":
            body = zlib.decompress(body)
    except (OSError, EOFError, zlib.error) as e:
        # A page cut off at the size limit can't be decompressed
        raise LinkPreviewError("That page is too large or unreadable") from e

    if len(body) > max_bytes:
        raise LinkPreviewError("That page is too large")

    return body, headers, final_url


# --- Parsing ---------------------------------------------------------------


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.itemprops: dict[str, str] = {}
        self.json_ld: list[str] = []
        self.title = ""
        self.image_src = None
        # Amazon keeps its details out of meta tags, so read its markup too
        self.product_title = ""
        self.product_image = None
        self.offscreen_price = None
        self._capture = None  # (tag, field) whose text is being read
        self._in_title = False
        self._in_json_ld = False
        self._json_ld_buffer = []

    def handle_starttag(self, tag, attrs):
        attrs = {k.lower(): v for k, v in attrs if v is not None}

        if tag == "meta":
            key = attrs.get("property") or attrs.get("name") or attrs.get("itemprop")
            content = attrs.get("content")
            if key and content:
                self.meta.setdefault(key.lower(), content.strip())
        if tag == "title":
            self._in_title = True
        elif tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True
            self._json_ld_buffer = []
        elif tag == "link" and "image_src" in attrs.get("rel", "").lower().split():
            self.image_src = self.image_src or attrs.get("href")

        if attrs.get("id") == "landingImage":
            self.product_image = attrs.get("data-old-hires") or attrs.get("src")
        if self._capture is None:
            if attrs.get("id") == "productTitle" and not self.product_title:
                self._capture = (tag, "product_title")
            elif "a-offscreen" in attrs.get("class", "").split() and not self.offscreen_price:
                self._capture = (tag, "offscreen_price")

        if itemprop := attrs.get("itemprop"):
            value = attrs.get("content") or attrs.get("src")
            if value:
                self.itemprops.setdefault(itemprop.lower(), value.strip())

    def handle_endtag(self, tag):
        if self._capture and self._capture[0] == tag:
            field = self._capture[1]
            setattr(self, field, " ".join((getattr(self, field) or "").split()))
            self._capture = None
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_json_ld:
            self._in_json_ld = False
            self.json_ld.append("".join(self._json_ld_buffer))

    def handle_data(self, data):
        if self._capture:
            field = self._capture[1]
            setattr(self, field, (getattr(self, field) or "") + data)
        if self._in_title:
            self.title += data
        elif self._in_json_ld:
            self._json_ld_buffer.append(data)


def _types(node: dict) -> set[str]:
    types = node.get("@type", [])
    if isinstance(types, str):
        types = [types]
    return {str(t).rsplit("/", 1)[-1].lower() for t in types}


def _find_products(node) -> list[dict]:
    """Every schema.org Product (or ProductGroup) anywhere in the JSON-LD."""
    found = []
    if isinstance(node, list):
        for child in node:
            found += _find_products(child)
    elif isinstance(node, dict):
        if _types(node) & {"product", "productgroup", "individualproduct"}:
            found.append(node)
        for key in ("@graph", "mainEntity", "itemListElement", "item"):
            if key in node:
                found += _find_products(node[key])
    return found


def _first_text(value) -> str | None:
    if isinstance(value, list):
        for v in value:
            if text := _first_text(v):
                return text
        return None
    if isinstance(value, dict):
        return _first_text(value.get("url") or value.get("contentUrl") or value.get("@id"))
    if isinstance(value, (str, int, float)) and str(value).strip():
        return str(value).strip()
    return None


def _offer_price(offers):
    if isinstance(offers, list):
        for offer in offers:
            if (price := _offer_price(offer)) is not None:
                return price
        return None
    if isinstance(offers, dict):
        for key in ("price", "lowPrice", "highPrice"):
            if offers.get(key) not in (None, ""):
                return offers[key]
        if spec := offers.get("priceSpecification"):
            return _offer_price(spec)
        if nested := offers.get("offers"):
            return _offer_price(nested)
    return None


def parse_price(value) -> float | None:
    """Turn "$1,299.99", "1.299,99 €" or 12.5 into a float."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 2) if value >= 0 else None
    if not isinstance(value, str):
        return None

    match = re.search(r"\d[\d.,\s]*", value)
    if not match:
        return None
    number = re.sub(r"\s", "", match.group()).rstrip(".,")

    if "," in number and "." in number:
        # Whichever separator comes last is the decimal point
        if number.rfind(",") > number.rfind("."):
            number = number.replace(".", "").replace(",", ".")
        else:
            number = number.replace(",", "")
    elif "," in number:
        # "12,99" is a decimal, "1,299" is thousands
        if re.fullmatch(r"\d+,\d{1,2}", number):
            number = number.replace(",", ".")
        else:
            number = number.replace(",", "")
    elif number.count(".") > 1:
        number = number.replace(".", "")

    try:
        return round(float(number), 2)
    except ValueError:
        return None


def parse_page(html: str, base_url: str) -> tuple[str | None, float | None, str | None]:
    """Return the title, price and absolute image URL found in a page."""
    parser = _PageParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        # Keep whatever was read before the markup broke the parser
        pass

    products = []
    for block in parser.json_ld:
        try:
            products += _find_products(json.loads(block, strict=False))
        except ValueError:
            continue

    meta = parser.meta
    props = parser.itemprops

    title = (
        meta.get("og:title")
        or meta.get("twitter:title")
        or next((_first_text(p.get("name")) for p in products if p.get("name")), None)
        or props.get("name")
        or parser.product_title
        or parser.title
    )
    title = " ".join(title.split())[:MAX_TITLE_LENGTH] if title else None

    price = None
    for candidate in (
        meta.get("product:price:amount"),
        meta.get("og:price:amount"),
        *(_offer_price(p.get("offers")) for p in products),
        props.get("price"),
        meta.get("twitter:data1") if "price" in meta.get("twitter:label1", "").lower() else None,
        parser.offscreen_price,
    ):
        if candidate is not None and (price := parse_price(candidate)) is not None:
            break

    image = (
        meta.get("og:image:secure_url")
        or meta.get("og:image")
        or meta.get("og:image:url")
        or meta.get("twitter:image")
        or meta.get("twitter:image:src")
        or next((_first_text(p.get("image")) for p in products if p.get("image")), None)
        or props.get("image")
        or parser.product_image
        or parser.image_src
    )
    if image:
        image = urljoin(base_url, image)
        if urlparse(image).scheme not in ("http", "https"):
            image = None

    return title, price, image


def _decode(body: bytes, headers: Message) -> str:
    charset = headers.get_content_charset()
    if not charset:
        head = body[:4096].decode("ascii", errors="ignore")
        if found := re.search(r"""<meta[^>]+charset=["']?([\w-]+)""", head, re.I):
            charset = found.group(1)
    try:
        return body.decode(charset or "utf-8", errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def normalize_url(url: str) -> str:
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "http://" + url
    parsed = urlparse(url)
    if not parsed.hostname:
        raise LinkPreviewError("That doesn't look like a link")
    return url


# Titles of the bot-check, queue and "please wait" pages stores show instead
# of the product. Their title must never be mistaken for the item's name.
_INTERSTITIAL_TITLE = re.compile(
    r"please wait|just a moment|one moment|checking your browser"
    r"|attention required|access denied|are you (a )?(robot|human)|robot or human"
    r"|verify(ing)? (that )?you are (a )?human|security check|captcha"
    r"|pardon (our|the) interruption|request (unsuccessful|blocked)"
    r"|you('ve| have) been blocked|too many requests|you are in (the )?queue",
    re.IGNORECASE,
)


def is_interstitial(title: str | None) -> bool:
    return bool(title) and _INTERSTITIAL_TITLE.search(title) is not None


def _details_in_browser(url: str):
    """Title, price, image URL and final URL from a page loaded in a browser.

    Returns None when no browser is available.
    """
    from . import browser_preview

    if not browser_preview.available():
        return None

    html, final_url, status = browser_preview.render(url)
    title, cost, image_url = parse_page(html, final_url)
    if title is None and cost is None and image_url is None and status >= 400:
        raise LinkPreviewError(f"The website responded with an error ({status})")
    return title, cost, image_url, final_url


def preview(url: str) -> LinkPreview:
    """Fetch a page and return whatever item details can be found on it.

    A plain request is tried first. If the store refuses it, or the page it
    returns has neither a price nor an image (often a bot-check page), the
    page is loaded in a headless browser instead, when one is installed.
    """
    url = normalize_url(url)
    direct_image = None

    try:
        body, headers, final_url = _fetch(url, MAX_PAGE_BYTES)
    except FetchRefusedError as plain_error:
        try:
            found = _details_in_browser(url)
        except LinkPreviewError:
            raise plain_error
        if found is None:
            raise plain_error
        title, cost, image_url, final_url = found
    else:
        if headers.get_content_maintype() == "image":
            # A direct link to a picture: use it as the image
            title, cost, image_url = None, None, final_url
            direct_image = (body, headers)
        else:
            title, cost, image_url = parse_page(_decode(body, headers), final_url)

            if cost is None and image_url is None:
                try:
                    found = _details_in_browser(url)
                except LinkPreviewError:
                    found = None
                if found:
                    b_title, b_cost, b_image_url, b_final_url = found
                    if b_cost is not None or b_image_url is not None:
                        title, cost, image_url, final_url = (
                            b_title or title, b_cost, b_image_url, b_final_url
                        )

    # Only a page with no product details at all is judged by its title, so
    # a real product that happens to be called "Please Wait" still works
    if cost is None and image_url is None and is_interstitial(title):
        raise LinkPreviewError(
            "The store showed a bot check page instead of the product"
        )

    result = LinkPreview(title=title, cost=cost)

    if image_url:
        try:
            if direct_image:
                image_body, image_headers = direct_image
            else:
                image_body, image_headers, _ = _fetch(image_url, MAX_IMAGE_BYTES)
        except LinkPreviewError:
            # A missing image shouldn't throw away the title and price
            image_body = None

        if image_body and image_headers.get_content_maintype() == "image":
            result.image = b64encode(image_body).decode("ascii")
            result.image_type = image_headers.get_content_type()
            name = PurePosixPath(urlparse(image_url).path).name
            result.image_name = name[:100] or "image"

    return result
