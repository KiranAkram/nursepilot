"""Offline: Jev is mocked at the HTTP layer via httpx.MockTransport."""

import io
import json

import httpx
import pytest
from pypdf import PdfWriter

import screening
from screening import (
    NotAnSnfPacketError,
    ScreeningUnavailableError,
    head_text,
    screen_pdf,
)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    monkeypatch.setattr(screening.time, "sleep", lambda s: None)


@pytest.fixture
def text(monkeypatch):
    """Skip pypdf; pretend the PDF has discharge-summary text."""
    monkeypatch.setattr(
        screening, "head_text", lambda pdf, pages=2: "DISCHARGE SUMMARY\nPatient: Doe, Jane"
    )


def _jev(score: float, *, seen: list | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        assert request.headers["authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["questions"]["is_snf_packet"]["type"] == "noul"
        return httpx.Response(
            200,
            json={"model": "jev-1.13.0", "answers": {"is_snf_packet": {"type": "noul", "noul": score}}},
        )

    return handler


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_accepted_returns_verdict(text):
    seen = []
    verdict = screen_pdf(b"%PDF", http=_client(_jev(0.93, seen=seen)))
    assert verdict["outcome"] == "accepted"
    assert verdict["score"] == 0.93
    assert verdict["threshold"] == 0.5
    assert verdict["model"] == "jev-1.13.0"
    assert json.loads(seen[0].content)["state"].startswith("DISCHARGE SUMMARY")


def test_rejected_raises_with_verdict(text):
    with pytest.raises(NotAnSnfPacketError) as info:
        screen_pdf(b"%PDF", http=_client(_jev(0.07)))
    assert info.value.screening["outcome"] == "rejected"
    assert info.value.screening["score"] == 0.07


def test_threshold_is_applied(text, monkeypatch):
    monkeypatch.setattr(screening, "THRESHOLD", 0.9)
    with pytest.raises(NotAnSnfPacketError):
        screen_pdf(b"%PDF", http=_client(_jev(0.8)))


def test_transient_error_then_success(text):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(503)
        return _jev(0.9)(request)

    assert screen_pdf(b"%PDF", http=_client(handler))["outcome"] == "accepted"
    assert len(calls) == 2


def test_persistent_outage_is_unavailable(text):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503)

    with pytest.raises(ScreeningUnavailableError, match="HTTP 503"):
        screen_pdf(b"%PDF", http=_client(handler))
    assert len(calls) == screening._MAX_ATTEMPTS


def test_network_failure_is_unavailable(text):
    def handler(request):
        raise httpx.ConnectError("boom")

    with pytest.raises(ScreeningUnavailableError, match="request failed"):
        screen_pdf(b"%PDF", http=_client(handler))


def test_malformed_response_is_unavailable(text):
    with pytest.raises(ScreeningUnavailableError, match="unexpected"):
        screen_pdf(b"%PDF", http=_client(lambda r: httpx.Response(200, json={})))


def test_missing_key_is_unavailable_without_calling(text, monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY")
    calls = []
    with pytest.raises(ScreeningUnavailableError, match="TYPESAFE_API_KEY"):
        screen_pdf(b"%PDF", http=_client(lambda r: calls.append(r)))
    assert calls == []


def test_no_text_is_unavailable_without_calling(monkeypatch):
    monkeypatch.setattr(screening, "head_text", lambda pdf, pages=2: "")
    calls = []
    with pytest.raises(ScreeningUnavailableError, match="no extractable text"):
        screen_pdf(b"%PDF", http=_client(lambda r: calls.append(r)))
    assert calls == []


def test_head_text_of_blank_pdf_is_empty():
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    assert head_text(buf.getvalue()) == ""
