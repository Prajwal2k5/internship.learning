
import pytest

from backend.services import rag_service


class FakeAPIError(Exception):
    def __init__(self, status_code):
        super().__init__(f"API error: {status_code}")
        self.status_code = status_code


# Test 1: Temporary server and rate-limit errors should be retryable
@pytest.mark.parametrize(
    "status_code",
    [408, 429, 500, 502, 503, 504]
)
def test_retryable_status_codes(status_code):
    error = FakeAPIError(status_code)
    assert rag_service.is_retryable_error(error) is True


# Test 2: Client errors should not be retried
@pytest.mark.parametrize(
    "status_code",
    [400, 401, 403, 404]
)
def test_non_retryable_status_codes(status_code):
    error = FakeAPIError(status_code)
    assert rag_service.is_retryable_error(error) is False


# Test 3: Network failures should be retryable
@pytest.mark.parametrize(
    "error",
    [TimeoutError(), ConnectionError()]
)
def test_network_errors(error):
    assert rag_service.is_retryable_error(error) is True


# Test 4: Unknown errors should not be retried
def test_unknown_error():
    assert rag_service.is_retryable_error(RuntimeError()) is False


# Test 5: Temporary failure should retry and eventually succeed
def test_retry_until_success(monkeypatch):
    monkeypatch.setattr(rag_service.time, "sleep", lambda _: None)

    attempts = {"count": 0}

    def operation():
        attempts["count"] += 1

        if attempts["count"] < 3:
            raise FakeAPIError(503)

        return "Success"

    result = rag_service.call_with_retry(
        operation, "Test operation"
    )

    assert result == "Success"
    assert attempts["count"] == 3


# Test 6: Authentication errors should stop immediately
def test_authentication_error_no_retry(monkeypatch):
    monkeypatch.setattr(rag_service.time, "sleep", lambda _: None)

    attempts = {"count": 0}

    def operation():
        attempts["count"] += 1
        raise FakeAPIError(401)

    with pytest.raises(FakeAPIError):
        rag_service.call_with_retry(
            operation, "Authentication test"
        )

    assert attempts["count"] == 1


# Test 7: Unknown errors should stop immediately
def test_unknown_error_no_retry(monkeypatch):
    monkeypatch.setattr(rag_service.time, "sleep", lambda _: None)

    attempts = {"count": 0}

    def operation():
        attempts["count"] += 1
        raise RuntimeError("Unexpected error")

    with pytest.raises(RuntimeError):
        rag_service.call_with_retry(
            operation, "Unknown error test"
        )

    assert attempts["count"] == 1


# Test 8: Exhausted retries should raise the final error
def test_max_retries_exhausted(monkeypatch):
    monkeypatch.setattr(rag_service.time, "sleep", lambda _: None)

    attempts = {"count": 0}

    def operation():
        attempts["count"] += 1
        raise FakeAPIError(503)

    with pytest.raises(FakeAPIError):
        rag_service.call_with_retry(
            operation, "Retry exhaustion test"
        )

    assert attempts["count"] == rag_service.MAX_RETRIES
