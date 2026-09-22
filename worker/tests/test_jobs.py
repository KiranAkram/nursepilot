import pytest

import jobs


class _FakeChart:
    def model_dump(self, mode="json"):
        return {"demographics": {"family_name": "A", "given_name": "B", "mrn": "M"}}


def _stub_pipeline(monkeypatch, calls):
    monkeypatch.setattr(
        jobs, "_persist", lambda job_id, **kw: calls.append((job_id, kw))
    )
    monkeypatch.setattr(jobs, "extract_chart_from_pdf", lambda pdf: (_FakeChart(), []))
    monkeypatch.setattr(jobs, "extract_page_texts", lambda pdf: [])
    monkeypatch.setattr(jobs, "verify_chart", lambda chart, texts: [])


def test_extract_chart_persists_done_once(monkeypatch):
    calls = []
    _stub_pipeline(monkeypatch, calls)

    result = jobs.extract_chart("job-1", b"%PDF")

    assert [(jid, kw["status"]) for jid, kw in calls] == [("job-1", "done")]
    done = calls[0][1]
    assert done["chart"] == {
        "demographics": {"family_name": "A", "given_name": "B", "mrn": "M"}
    }
    assert done["grounding"] == []
    assert result["chart"] == done["chart"]


def test_extract_chart_propagates_failure_without_persisting(monkeypatch):
    """Retry/error status is the queue's decision, so a failing job touches nothing."""
    calls = []
    _stub_pipeline(monkeypatch, calls)

    def boom(pdf):
        raise RuntimeError("gemini down")

    monkeypatch.setattr(jobs, "extract_chart_from_pdf", boom)

    with pytest.raises(RuntimeError, match="gemini down"):
        jobs.extract_chart("job-2", b"%PDF")
    assert calls == []
