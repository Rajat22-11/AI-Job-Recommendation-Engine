import logging

import pytest

from job_aggregator.credentials.credential_pool import CredentialPool, rotate_on_quota_error
from job_aggregator.credentials.secret_redaction import (
    SecretRedactingFilter,
    clear_registered_secrets,
    redact_secrets,
)
from job_aggregator.credentials.token_error_classifiers import (
    TokenFailure,
    classify_apify_failure,
    classify_gemini_failure,
)
from job_aggregator.domain.errors import AllTokensExhaustedError


class FakeApiError(Exception):
    def __init__(self, status_code, message):
        super().__init__(message)
        self.status_code = status_code


@pytest.fixture(autouse=True)
def _reset_secrets():
    clear_registered_secrets()
    yield
    clear_registered_secrets()


def test_several_tokens_kept_in_order_and_first_used():
    pool = CredentialPool("apify", ["tok-aaaa", "tok-bbbb", "tok-cccc"])
    used = []
    assert rotate_on_quota_error(pool, lambda t: used.append(t) or "ok") == "ok"
    assert used == ["tok-aaaa"]
    assert pool.available_positions() == [1, 2, 3]


def test_single_token_behaves_as_pool_of_one():
    pool = CredentialPool("apify", ["only-token"])
    assert rotate_on_quota_error(pool, lambda t: t) == "only-token"


def test_rotates_on_quota_and_marks_first_unavailable():
    pool = CredentialPool("apify", ["tok-aaaa", "tok-bbbb"])

    def call(token):
        if token == "tok-aaaa":
            raise FakeApiError(402, "Monthly usage limit exceeded")
        return "second"

    assert rotate_on_quota_error(pool, call) == "second"
    assert pool.available_positions() == [2]


def test_does_not_rotate_on_malformed_request():
    pool = CredentialPool("apify", ["tok-aaaa", "tok-bbbb"])
    with pytest.raises(FakeApiError):
        rotate_on_quota_error(pool, lambda t: (_ for _ in ()).throw(FakeApiError(400, "invalid input")))
    assert pool.available_positions() == [1, 2]


def test_later_call_skips_unavailable_token():
    pool = CredentialPool("gemini", ["key-aaaa", "key-bbbb"])
    pool.mark_unavailable(1, "quota exhausted")
    used = []
    rotate_on_quota_error(pool, lambda t: used.append(t))
    assert used == ["key-bbbb"]


def test_all_tokens_exhausted_raises_naming_service():
    pool = CredentialPool("apify", ["tok-aaaa", "tok-bbbb"])
    with pytest.raises(AllTokensExhaustedError, match="apify"):
        rotate_on_quota_error(pool, lambda t: (_ for _ in ()).throw(FakeApiError(429, "rate limit")))
    with pytest.raises(AllTokensExhaustedError, match="No tokens are configured for service 'gemini'"):
        rotate_on_quota_error(CredentialPool("gemini", []), lambda t: t)


@pytest.mark.parametrize(
    ("classifier", "exc", "expected"),
    [
        (classify_apify_failure, FakeApiError(429, "too many"), TokenFailure.RATE_LIMITED),
        (classify_apify_failure, FakeApiError(401, "User was not found or authentication token is not valid"),
         TokenFailure.TOKEN_REJECTED),
        (classify_apify_failure, FakeApiError(500, "server error"), None),
        (classify_gemini_failure, FakeApiError(429, "RESOURCE_EXHAUSTED quota"), TokenFailure.QUOTA_EXHAUSTED),
        (classify_gemini_failure, FakeApiError(400, "API key not valid"), TokenFailure.TOKEN_REJECTED),
        (classify_gemini_failure, FakeApiError(400, "bad json"), None),
    ],
)
def test_classifiers(classifier, exc, expected):
    assert classifier(exc) == expected


def test_token_values_never_appear_in_logs(caplog):
    caplog.handler.addFilter(SecretRedactingFilter())
    pool = CredentialPool("apify", ["apify_api_SECRETVALUE1", "apify_api_SECRETVALUE2"])

    def call(token):
        raise FakeApiError(402, f"usage limit reached for token {token}")

    with caplog.at_level(logging.DEBUG), pytest.raises(AllTokensExhaustedError) as info:
        rotate_on_quota_error(pool, call)
    logging.getLogger("test").error("failed with %s", "apify_api_SECRETVALUE1", exc_info=True)
    output = caplog.text + str(info.value)
    assert "SECRETVALUE" not in output
    assert "apify token #1" in output
    assert redact_secrets("x apify_api_SECRETVALUE2 y") == "x <apify token #2> y"
