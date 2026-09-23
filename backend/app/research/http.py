"""Outbound HTTP for the worker. SSRF-safe by construction: https only, fixed host allowlist, no redirects,
bounded body size and timeouts. Secrets in query strings are never echoed into errors."""

import threading
import time
from collections.abc import Callable
from urllib.parse import urlsplit

import httpx

ALLOWED_HOSTS = frozenset({"eutils.ncbi.nlm.nih.gov", "www.ebi.ac.uk", "api.openai.com",
                          "en.wikipedia.org", "commons.wikimedia.org", "upload.wikimedia.org"})

# One more trusted host, added once at process startup: the operator's own Supabase project (its host
# varies per deployment, so it can't be a fixed literal above). Never attacker-influenced.
_extra_allowed_host: str | None = None


def configure_allowed_host(host: str) -> None:
    global _extra_allowed_host
    _extra_allowed_host = host.lower()


class FetchError(Exception):
    """code is stable and safe to store in research_jobs.last_error; retryable drives fail_job."""

    def __init__(self, code: str, retryable: bool, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code, self.retryable, self.detail = code, retryable, detail


class RateLimiter:
    """Minimum spacing between calls, shared across threads."""

    def __init__(self, per_second: float, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        self.interval = 1.0 / per_second
        self._clock, self._sleep = clock, sleep
        self._next = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = self._clock()
            delay = self._next - now
            self._next = max(now, self._next) + self.interval
        if delay > 0:
            self._sleep(delay)


def check_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise FetchError("url_blocked", False, "https only")
    if parts.username or parts.password or "@" in parts.netloc:
        raise FetchError("url_blocked", False, "credentials in url")
    if parts.port not in (None, 443):
        raise FetchError("url_blocked", False, "port not allowed")
    host = (parts.hostname or "").lower()
    if host not in ALLOWED_HOSTS and host != _extra_allowed_host:
        raise FetchError("url_blocked", False, f"host not allowed: {parts.hostname}")


def _status_error(status: int) -> FetchError:
    if status == 429 or status >= 500:
        return FetchError("upstream_unavailable", True, f"http {status}")
    return FetchError("upstream_rejected", False, f"http {status}")


class SafeClient:
    def __init__(self, transport: httpx.BaseTransport | None = None, max_bytes: int = 5_000_000,
                 timeout: httpx.Timeout | None = None, user_agent: str = "herbal-evidence/0.1"):
        self.max_bytes = max_bytes
        self._http = httpx.Client(transport=transport, follow_redirects=False,
                                  timeout=timeout or httpx.Timeout(20, connect=5),
                                  headers={"User-Agent": user_agent})

    def close(self) -> None:
        self._http.close()

    def get(self, url: str, *, params: dict | None = None, limiter: RateLimiter | None = None,
            timeout: float | None = None) -> httpx.Response:
        return self._send("GET", url, params=params, limiter=limiter, timeout=timeout)

    def post_json(self, url: str, body: dict, *, headers: dict | None = None,
                  timeout: float | None = None) -> httpx.Response:
        return self._send("POST", url, json=body, headers=headers, timeout=timeout)

    def post_bytes(self, url: str, content: bytes, *, headers: dict | None = None,
                   timeout: float | None = None) -> httpx.Response:
        return self._send("POST", url, content=content, headers=headers, timeout=timeout)

    def _send(self, method: str, url: str, *, limiter: RateLimiter | None = None, timeout: float | None = None,
              **kwargs) -> httpx.Response:
        check_url(url)
        if limiter:
            limiter.wait()
        if timeout is not None:
            kwargs["timeout"] = timeout
        try:
            with self._http.stream(method, url, **kwargs) as r:
                if r.is_redirect:
                    raise FetchError("redirect_blocked", False, f"http {r.status_code}")
                if r.status_code >= 400:
                    raise _status_error(r.status_code)
                body = bytearray()
                for chunk in r.iter_bytes():
                    body += chunk
                    if len(body) > self.max_bytes:
                        raise FetchError("response_too_large", False)
                # body is already decoded: drop the encoding headers or httpx would decode it twice
                headers = [(k, v) for k, v in r.headers.items() if k.lower() not in ("content-encoding", "content-length")]
                return httpx.Response(r.status_code, headers=headers, content=bytes(body), request=r.request)
        except httpx.TimeoutException:
            raise FetchError("upstream_timeout", True) from None
        except httpx.HTTPError as e:
            # the exception text can contain the full URL (with api_key): keep only the type
            raise FetchError("upstream_unreachable", True, type(e).__name__) from None
