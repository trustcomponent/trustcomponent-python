import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import UUID

import pytest

from trustcomponent import TrustComponent
from trustcomponent.errors import ConflictError, NotFoundError, OperationRetiredError, RateLimitError, VerificationTokenInvalidError

ID = "cc2e2d5e-d1ef-4a7f-a7bd-dec5b37df47a"
T = "2020-01-01T13:30:05.941Z"
RESULT = {"captchaId": ID, "verificationId": ID, "verificationPassed": True, "score": 0.3, "decisionType": "STANDARD", "decisionAction": "ALLOW",
          "gatewayFailoverActive": False, "riskScoringEnabled": True, "minimalDataModeEnabled": False, "origin": "https://example.com",
          "ipAddress": "1.2.3.4", "countryCode": "DE", "deviceFamily": "Desktop", "operatingSystem": "Linux", "browser": "Firefox",
          "verificationStartedAt": T, "verificationFinishedAt": T, "resultExpiresAt": T, "resultFirstFetchedAt": T, "resultLastFetchedAt": T}


def ok(headers=None):
    return 200, {"Content-Type": "application/json", **(headers or {})}, RESULT


def problem(status, code):
    return status, {"Content-Type": "application/problem+json"}, {"status": status, "code": code, "detail": "detail"}


@pytest.fixture
def server():
    requests, answers = [], []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            requests.append(self)
            status, headers, body = answers[min(len(requests) - 1, len(answers) - 1)]
            data = b"" if body is None else json.dumps(body).encode()
            self.send_response(status)
            for k, v in headers.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_POST = do_GET

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    warnings = []

    def client(*a):
        answers.extend(a)
        return TrustComponent("ak_test", host=f"http://127.0.0.1:{httpd.server_address[1]}", integration="test-suite/1.0", logger=warnings.append)

    yield client, requests, warnings
    httpd.shutdown()


def token(client_failover):
    return base64.b64encode(json.dumps({"verificationId": ID, "clientFailover": client_failover}).encode()).decode()


def test_sends_key_user_agent_and_metadata_and_decodes_the_widget_token(server):
    client, requests, _ = server
    result = client(ok()).captcha.get_verification_result(token(True))
    assert result.verification_passed is True
    assert requests[0].path == f"/captcha/v2/verifications/{ID}/results?clientFailover=true"
    assert requests[0].headers["Authorization"] == "Bearer ak_test"
    assert requests[0].headers["User-Agent"].startswith("trustcomponent-python/")
    metadata = json.loads(base64.b64decode(requests[0].headers["TrustComponent-Sdk"]))
    assert metadata["sdk"] == "python" and metadata["integration"] == "test-suite/1.0"


def test_an_invalid_widget_token_fails_before_any_request(server):
    client, requests, _ = server
    with pytest.raises(VerificationTokenInvalidError):
        client(ok()).captcha.get_verification_result("not-a-token")
    assert requests == []


def test_retries_503_and_429_with_retry_after_then_succeeds(server):
    client, requests, _ = server
    client((503, {}, None), (429, {"Retry-After": "0"}, None), ok()).captcha.verifications.get_result(UUID(ID))
    assert len(requests) == 3


def test_a_429_without_retry_after_is_final_and_not_retried(server):
    client, requests, _ = server
    with pytest.raises(RateLimitError):
        client((429, {}, None), ok()).captcha.verifications.get_result(UUID(ID))
    assert len(requests) == 1


def test_problem_details_become_typed_errors_with_the_code_of_the_api(server):
    client, _, _ = server
    with pytest.raises(NotFoundError) as e:
        client(problem(404, "validation_result_not_found")).tax_validation.validation_results.get_validation_result(UUID(ID))
    assert e.value.code == "validation_result_not_found" and e.value.status == 404


def test_a_client_failover_rejected_by_the_gateway_is_a_conflict(server):
    client, _, _ = server
    with pytest.raises(ConflictError):
        client((412, {}, {"reason": "CLIENT_FAILOVER_REJECTED"})).captcha.get_verification_result(token(True))


def test_a_deprecated_operation_warns_once_a_retired_one_asks_for_an_update(server):
    client, _, warnings = server
    deprecated = {"Deprecation": "@1799971200", "Sunset": "Thu, 15 Jul 2027 00:00:00 GMT"}
    tc = client(ok(deprecated), ok(deprecated), problem(410, "operation_retired"))
    tc.captcha.verifications.get_result(UUID(ID))
    tc.captcha.verifications.get_result(UUID(ID))
    assert len(warnings) == 1 and "15 Jul 2027" in warnings[0]
    with pytest.raises(OperationRetiredError):
        tc.platform.events.get_events()
