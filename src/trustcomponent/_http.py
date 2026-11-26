from __future__ import annotations

import json
import random
import re
import threading
import time
from email.utils import parsedate_to_datetime
from typing import Callable, Optional

import urllib3

from trustcomponent._generated.api_client import ApiClient
from trustcomponent.errors import ConnectionError, error_of

_RETRYABLE_STATUS = {502, 503, 504}
_MAX_RETRY_AFTER_SECONDS = 60
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f-]{27}", re.IGNORECASE)
_warned: set[str] = set()
_warned_lock = threading.Lock()


class SdkApiClient(ApiClient):
    """The single HTTP path of the SDK: retries what the API reserves for retries (429 with Retry-After, 502/503/504,
    no response at all), warns once per deprecated operation and turns every other non-2xx answer into a typed
    TrustComponentError before the generated code sees it."""

    def __init__(self, configuration, timeout: float, max_retries: int, deprecation_warnings: bool, warn: Callable[[str], None]) -> None:
        super().__init__(configuration)
        self._timeout = timeout
        self._max_retries = max_retries
        self._deprecation_warnings = deprecation_warnings
        self._warn = warn

    def call_api(self, method, url, header_params=None, body=None, post_params=None, _request_timeout=None):
        attempt = 0
        while True:
            try:
                response = super().call_api(method, url, header_params, body, post_params, _request_timeout or self._timeout)
            except urllib3.exceptions.HTTPError as e:
                if attempt < self._max_retries:
                    time.sleep(_backoff(attempt))
                    attempt += 1
                    continue
                raise ConnectionError(f"TrustComponent API not reachable: {e}") from e
            response.read()
            self._warn_if_deprecated(method, url, response)
            if 200 <= response.status < 300:
                return response
            retry_after = _retry_after_seconds(response.getheader("Retry-After"))
            retryable = response.status in _RETRYABLE_STATUS or (response.status == 429 and retry_after is not None)
            if retryable and attempt < self._max_retries and (retry_after or 0) <= _MAX_RETRY_AFTER_SECONDS:
                time.sleep(retry_after if retry_after is not None else _backoff(attempt))
                attempt += 1
                continue
            raise error_of(response.status, _problem_of(response.data), retry_after)

    def _warn_if_deprecated(self, method: str, url: str, response) -> None:
        if not self._deprecation_warnings or response.getheader("Deprecation") is None:
            return
        operation = f"{method.upper()} {_UUID.sub('{id}', urllib3.util.parse_url(url).path or '')}"
        with _warned_lock:
            if operation in _warned:
                return
            _warned.add(operation)
        sunset = response.getheader("Sunset")
        self._warn(f"TrustComponent: {operation} is deprecated" + (f" and will be switched off on {sunset}" if sunset else "") + ". Update the TrustComponent SDK.")


def _backoff(attempt: int) -> float:
    return min(0.5 * 2 ** attempt, 8.0) + random.random() * 0.25


def _retry_after_seconds(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return max(0, int(value.strip()))
    except ValueError:
        try:
            return max(0, int(parsedate_to_datetime(value).timestamp() - time.time()))
        except (TypeError, ValueError):
            return None


def _problem_of(data: Optional[bytes]):
    try:
        return json.loads(data) if data else None
    except ValueError:
        return None
