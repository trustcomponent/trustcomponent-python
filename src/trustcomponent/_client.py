from __future__ import annotations

import base64
import json
import logging
import platform
from typing import Callable, Optional

from trustcomponent._generated.configuration import Configuration
from trustcomponent._generated.modules import API_VERSION, SDK_VERSION, AnalyticsModule, MonitoringModule, PlatformModule, TaxValidationModule
from trustcomponent._http import SdkApiClient
from trustcomponent.captcha import CaptchaModule

DEFAULT_HOST = "https://api.trustcomponent.com"
_logger = logging.getLogger("trustcomponent")


class TrustComponent:
    """Entry point of the SDK. ``TrustComponent("ak_…")`` is all most integrations need; keyword arguments change host,
    timeout, proxy, retries and the rest."""

    version = SDK_VERSION

    def __init__(
        self,
        api_key: str,
        *,
        host: str = DEFAULT_HOST,
        timeout: float = 10.0,
        proxy: Optional[str] = None,
        max_retries: int = 2,
        deprecation_warnings: bool = True,
        integration: Optional[str] = None,
        logger: Callable[[str], None] = _logger.warning,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("api_key must not be empty")
        configuration = Configuration(host=host.rstrip("/"), access_token=api_key.strip(), retries=False, proxy=proxy)
        client = SdkApiClient(configuration, timeout, max(0, max_retries), deprecation_warnings, logger)
        client.user_agent = f"trustcomponent-python/{SDK_VERSION}"
        client.set_default_header("Authorization", f"Bearer {api_key.strip()}")
        client.set_default_header("TrustComponent-Sdk", _sdk_header(integration))
        self.captcha = CaptchaModule(client)
        self.analytics = AnalyticsModule(client)
        self.monitoring = MonitoringModule(client)
        self.tax_validation = TaxValidationModule(client)
        self.platform = PlatformModule(client)


def _sdk_header(integration: Optional[str]) -> str:
    metadata = {"sdk": "python", "version": SDK_VERSION, "api": API_VERSION, "runtime": f"python/{platform.python_version()}", "os": platform.system()}
    if integration:
        metadata["integration"] = integration
    return base64.b64encode(json.dumps(metadata, separators=(",", ":")).encode()).decode()
