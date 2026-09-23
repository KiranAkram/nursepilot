import pytest

import jobs
from screening import NotAnSnfPacketError


class _FakeChart:
    def model_dump(self, mode="json"):
        return {"demographics": {"family_name": "A", "given_name": "B", "mrn": "M"}}


VERDICT = {"outcome": "accepted", "score": 0.9}


def _stub_pipeline(monkeypatch, calls):
    monkeypatch.setattr(
        jobs, "_persist", lambda job_id, **kw: calls.append((job_id, kw))
    )
    monkeypatch.setattr(jobs, "screen_pdf", lambda pdf: VERDICT)
    monkeypatch.setattr(jobs, "extract_chart_from_pdf", lambda pdf: (_FakeChart(), []))
    monkeypatch.setattr(jobs, "extract_page_texts", lambda pdf: [])
    monkeypatch.setattr(jobs, "verify_chart", lambda chart, texts: [])


def test_extract_chart_screens_then_persists_done(monkeypatch):
    calls = []
    _stub_pipeline(monkeypatch, calls)

    result = jobs.extract_chart("job-1", b"%PDF")

    assert [(jid, kw["status"]) for jid, kw in calls] == [
        ("job-1", "extracting"),
        ("job-1", "done"),
    ]
    assert calls[0][1]["screening"] == VERDICT
    done = calls[1][1]
    assert done["chart"] == {
        "demographics": {"family_name": "A", "given_name": "B", "mrn": "M"}
    }
    assert done["grounding"] == []
    assert result["chart"] == done["chart"]


def test_extraction_failure_leaves_row_extracting_never_done(monkeypatch):
    """Screening passed (row -> extracting), Gemini failed: no `done`, exception
    propagates so the queue decides retry-vs-error."""
    calls = []
    _stub_pipeline(monkeypatch, calls)

    def boom(pdf):
        raise RuntimeError("gemini down")

    monkeypatch.setattr(jobs, "extract_chart_from_pdf", boom)

    with pytest.raises(RuntimeError, match="gemini down"):
        jobs.extract_chart("job-2", b"%PDF")
    assert [(jid, kw["status"]) for jid, kw in calls] == [("job-2", "extracting")]


def test_rejected_by_screening_propagates_before_extraction(monkeypatch):
    calls = []
    _stub_pipeline(monkeypatch, calls)
    extracted = []
    monkeypatch.setattr(jobs, "extract_chart_from_pdf", lambda pdf: extracted.append(pdf))

    def no(pdf):
        raise NotAnSnfPacketError({"outcome": "rejected", "score": 0.1})

    monkeypatch.setattr(jobs, "screen_pdf", no)

    with pytest.raises(NotAnSnfPacketError):
        jobs.extract_chart("job-3", b"%PDF")
    assert calls == []
    assert extracted == []
