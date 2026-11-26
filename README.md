# TrustComponent SDK for Python

The official SDK for the TrustComponent API: TrustCaptcha, TrustAnalytics, TrustMonitoring, Trust VAT Checker and the
platform API, in one package. Developed and hosted in the EU.

Requires Python 3.9 or newer.

## Install

```sh
pip install trustcomponent
```

## Check a TrustCaptcha result

The widget writes a verification token into your form. One call turns it into the result:

```python
from trustcomponent import TrustComponent

tc = TrustComponent("ak_…")
result = tc.captcha.get_verification_result(request.form["tc-verification-token"])
if result.verification_passed:
    ...
```

Create the API key (`ak_…`) in the dashboard under the project's API keys. The key decides which modules the client can use.

## Every module

The client is `module → resource → operation`, with the same names in every language:

```python
from trustcomponent import models

tc.analytics.websites.get_websites()
tc.tax_validation.validations.create_validation(models.TaxValidationValidationCreateParams(countryCode="DE", rawValue="DE811569869"))
tc.monitoring.heartbeats.ping_heartbeat(service_id, monitor_id)
tc.platform.events.get_events()
```

The full reference of every operation is at https://docs.trustcomponent.com.

## Configuration

```python
tc = TrustComponent("ak_…", timeout=5, max_retries=1, integration="my-plugin/1.0")
```

Options: `host`, `timeout`, `proxy`, `max_retries`, `deprecation_warnings`, `integration`, `logger`.

The SDK retries only what the API reserves for retries: `429` with `Retry-After`, `502`, `503`, `504` and a lost
connection (2 retries by default). When the API marks an operation as deprecated, it logs one warning per operation.
Every request names the SDK in `User-Agent` and `TrustComponent-Sdk`, together with the integration you set.

## Errors

Every error is a `trustcomponent.TrustComponentError` carrying the HTTP status and the stable `code` of the API:
`InvalidRequestError`, `AuthenticationError`, `PermissionDeniedError`, `PlanLimitError`, `NotFoundError`, `ConflictError`, `GoneError`, `RateLimitError`, `ServerError`, `ConnectionError`, `OperationRetiredError`, `VerificationTokenInvalidError`.

```python
from trustcomponent import NotFoundError

try:
    tc.captcha.get_verification_result(token)
except NotFoundError as e:
    print(e.status, e.code)
```

`OperationRetired` means the operation was switched off after its sunset: update the SDK.

## Support

The GitHub repository of this SDK is a read-only mirror, generated from the TrustComponent API, so pull requests and
issues are not processed there. For questions and bug reports, write to mail@trustcomponent.com or contact support
through https://www.trustcomponent.com.

## License

MIT
