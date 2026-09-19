"""Allowlisted HTTPS fetch for MaxPreps / SixManFootball / DCTF.

Mirrors sixmanmadness ``safe-fetch.ts``: browser UA, https only, Cloudflare
challenge detection, optional reader fallback so GitHub Actions can pull
scoreboards when a raw curl is challenged.
"""

from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

ALLOWED_HOSTS = {
    "www.maxpreps.com",
    "maxpreps.com",
    "sixmanfootball.com",
    "www.sixmanfootball.com",
    "www.texasfootball.com",
    "texasfootball.com",
    "r.jina.ai",
}

CHALLENGE = (
    "cf-browser-verification",
    "just a moment",
    "performing security verification",
    "enable javascript and cookies to continue",
)


class FetchError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status


def _assert_safe(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise FetchError("only https URLs are allowed")
    if parsed.username or parsed.password:
        raise FetchError("credentials in URLs are not allowed")
    host = (parsed.hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise FetchError(f"host not allowlisted: {host}")
    return parsed.geturl()


def is_challenge(body: str) -> bool:
    sample = body[:20_000].lower()
    return any(token in sample for token in CHALLENGE) and len(body) < 40_000


def fetch_text(
    url: str,
    *,
    timeout: float = 20.0,
    referer: str | None = None,
    accept: str = "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
) -> str:
    safe = _assert_safe(url)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": accept,
        "Accept-Language": "en-US,en;q=0.9",
    }
    if referer:
        headers["Referer"] = referer
    req = Request(safe, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            status = getattr(resp, "status", 200)
    except HTTPError as exc:
        raise FetchError(f"HTTP {exc.code} from {safe}", status=exc.code) from exc
    except URLError as exc:
        raise FetchError(f"network error from {safe}: {exc.reason}") from exc
    if status >= 400:
        raise FetchError(f"HTTP {status} from {safe}", status=status)
    body = raw.decode("utf-8", "replace")
    if is_challenge(body):
        raise FetchError("Cloudflare challenge", status=403)
    return body


def post_json(
    url: str,
    payload: dict,
    *,
    timeout: float = 20.0,
    referer: str | None = None,
) -> dict | list | str:
    """POST JSON to an allowlisted host. Returns parsed JSON when possible."""

    safe = _assert_safe(url)
    raw_body = json.dumps(payload).encode("utf-8")
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
    }
    if referer:
        headers["Referer"] = referer
    req = Request(safe, data=raw_body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            status = getattr(resp, "status", 200)
    except HTTPError as exc:
        raise FetchError(f"HTTP {exc.code} from {safe}", status=exc.code) from exc
    except URLError as exc:
        raise FetchError(f"network error from {safe}: {exc.reason}") from exc
    if status >= 400:
        raise FetchError(f"HTTP {status} from {safe}", status=status)
    text = raw.decode("utf-8", "replace")
    if is_challenge(text):
        raise FetchError("Cloudflare challenge", status=403)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def fetch_with_fallback(
    url: str,
    *,
    timeout: float = 20.0,
    referer: str | None = None,
    reader: bool | None = None,
) -> tuple[str, str]:
    """Return ``(body, source)`` where source is ``direct`` or ``reader``."""

    use_reader = reader if reader is not None else os.environ.get("SIXMAN_USE_READER", "1") != "0"
    try:
        return fetch_text(url, timeout=timeout, referer=referer), "direct"
    except FetchError as exc:
        if not use_reader or exc.status == 404:
            raise
        reader_url = f"https://r.jina.ai/{url}"
        body = fetch_text(
            reader_url,
            timeout=max(timeout, 30.0),
            accept="text/plain,text/html,*/*",
        )
        if is_challenge(body) or len(body) < 200:
            raise FetchError(f"reader fallback empty for {url}") from exc
        return body, "reader"
