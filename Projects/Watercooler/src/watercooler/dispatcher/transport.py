"""Fail-closed Watercooler transport for the commit-review dispatcher."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Mapping
from urllib.parse import urlencode

from ..common import WatercoolerError

MAX_RESPONSE_BYTES = 2_000_000


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Turn every redirect into an HTTP error before credentials can move."""

    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def _build_opener() -> urllib.request.OpenerDirector:
    # The dispatcher endpoint is explicit policy. Environment proxies must not
    # reinterpret loopback or become an undeclared credential-bearing hop.
    return urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        NoRedirectHandler(),
    )


def request_json(
    config: Mapping[str, Any],
    *,
    method: str,
    path: str,
    payload: Mapping[str, Any] | None = None,
    query: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Call one exact Watercooler origin without redirects or proxy inheritance."""

    base_url = config.get("base_url")
    token = config.get("token")
    if type(base_url) is not str or not base_url.strip():
        raise WatercoolerError("dispatcher config has no usable base_url")
    if type(token) is not str or not token.strip():
        raise WatercoolerError("dispatcher config has no usable token")
    if (
        type(path) is not str
        or not path.startswith("/")
        or path.startswith("//")
        or "?" in path
        or "#" in path
        or any(ord(character) < 32 or ord(character) == 127 for character in path)
    ):
        raise WatercoolerError("dispatcher request path is malformed")

    url = base_url.rstrip("/") + path
    if query:
        filtered = {key: value for key, value in query.items() if value not in ("", None)}
        if filtered:
            url += "?" + urlencode(filtered)

    data = None
    headers = {"X-Watercooler-Token": token}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers, method=method.upper())

    try:
        with _build_opener().open(request, timeout=15) as response:
            if response.geturl() != url:
                raise WatercoolerError("dispatcher endpoint changed without authorization")
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise WatercoolerError("Watercooler response exceeds the dispatcher byte limit")
            decoded = json.loads(body.decode("utf-8"))
            if type(decoded) is not dict:
                raise WatercoolerError("Watercooler response root must be an object")
            return decoded
    except WatercoolerError:
        raise
    except urllib.error.HTTPError as exc:
        detail = exc.read(501).decode("utf-8", errors="replace")[:500]
        raise WatercoolerError(
            f"{method.upper()} {path} failed with HTTP {exc.code}: {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise WatercoolerError(f"{method.upper()} {path} failed: {exc}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WatercoolerError("Watercooler returned invalid JSON") from exc
