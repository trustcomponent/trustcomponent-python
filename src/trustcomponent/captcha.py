from __future__ import annotations

import base64
import binascii
import json
from typing import NamedTuple
from uuid import UUID

from trustcomponent._generated.models.captcha_verification_result import CaptchaVerificationResult
from trustcomponent._generated.modules import CaptchaModuleBase
from trustcomponent.errors import VerificationTokenInvalidError


class VerificationToken(NamedTuple):
    verification_id: UUID
    client_failover: bool


class CaptchaModule(CaptchaModuleBase):
    def get_verification_result(self, verification_token: str) -> CaptchaVerificationResult:
        """Returns the result of the verification behind a widget token, the one call a form handler needs.
        When the widget could not reach TrustCaptcha (``clientFailover`` in the token), the public gateway decides
        whether the visitor may pass."""
        token = parse_verification_token(verification_token)
        return self.verifications.get_result(token.verification_id, client_failover=True if token.client_failover else None)


def parse_verification_token(verification_token: str) -> VerificationToken:
    try:
        token = json.loads(base64.b64decode(verification_token.strip(), validate=True))
        return VerificationToken(UUID(token["verificationId"]), token.get("clientFailover") is True)
    except (binascii.Error, ValueError, KeyError, TypeError, AttributeError) as e:
        raise VerificationTokenInvalidError("The verification token is not a TrustCaptcha token", 0, "verification_token_invalid") from e
