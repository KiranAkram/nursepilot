"""Offline: drain() maps each job outcome to the right queue call."""

import listener
from screening import NotAnSnfPacketError, ScreeningUnavailableError


def _drain_with(monkeypatch, job, *, raises=None):
    jobs = [job]
    calls = {"fail": [], "reject": [], "done": []}
    monkeypatch.setattr(listener, "claim", lambda conn: jobs.pop(0) if jobs else None)
    monkeypatch.setattr(
        listener, "fail", lambda conn, jid, err, **kw: calls["fail"].append((jid, err, kw))
    )
    monkeypatch.setattr(listener, "reject", lambda conn, jid, s: calls["reject"].append((jid, s)))

    def run(jid, pdf):
        if raises is not None:
            raise raises
        calls["done"].append(jid)

    monkeypatch.setattr(listener, "extract_chart", run)
    assert listener.drain(conn=None) == 1
    return calls


def test_success_touches_nothing_else(monkeypatch):
    calls = _drain_with(monkeypatch, ("j1", b"%PDF"))
    assert calls == {"fail": [], "reject": [], "done": ["j1"]}


def test_not_a_packet_is_rejected_not_failed(monkeypatch):
    verdict = {"outcome": "rejected", "score": 0.1}
    calls = _drain_with(monkeypatch, ("j1", b"%PDF"), raises=NotAnSnfPacketError(verdict))
    assert calls["reject"] == [("j1", verdict)]
    assert calls["fail"] == []


def test_screening_outage_fails_with_verdict_and_retries(monkeypatch):
    calls = _drain_with(monkeypatch, ("j1", b"%PDF"), raises=ScreeningUnavailableError("down"))
    (jid, err, kw), = calls["fail"]
    assert (jid, err) == ("j1", "down")
    assert kw["screening"]["outcome"] == "unavailable"
    assert kw.get("retryable", True) is True


def test_other_errors_fail_normally(monkeypatch):
    calls = _drain_with(monkeypatch, ("j1", b"%PDF"), raises=RuntimeError("gemini"))
    (jid, err, kw), = calls["fail"]
    assert (jid, err, kw) == ("j1", "gemini", {})


def test_missing_pdf_fails_non_retryable(monkeypatch):
    calls = _drain_with(monkeypatch, ("j1", None))
    (jid, err, kw), = calls["fail"]
    assert jid == "j1" and "no PDF" in err and kw == {"retryable": False}
