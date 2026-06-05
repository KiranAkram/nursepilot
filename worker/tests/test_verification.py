from datetime import date, datetime

from schemas import PatientChart
from schemas.common import SourceRef
from schemas.patient_chart import Demographics, Encounter, Insurance
from verification import _collect_sources, _grounds, verify_chart


def _chart(pages: dict[str, int]) -> PatientChart:
    """Build a chart whose three sources quote the given (quote -> page)."""
    quotes = list(pages.items())
    return PatientChart(
        demographics=Demographics(
            family_name="Doe",
            given_name="Jane",
            dob=date(1950, 1, 1),
            gender="female",
            mrn="MRN1",
            source=SourceRef(page=quotes[0][1], quote=quotes[0][0], confidence=0.9),
        ),
        insurance=Insurance(
            coverage_type="Medicare Part A",
            source=SourceRef(page=quotes[1][1], quote=quotes[1][0], confidence=0.8),
        ),
        encounter=Encounter(
            status="finished",
            encounter_class="IMP",
            admit_start=datetime(2024, 1, 1),
            discharge_end=datetime(2024, 1, 5),
            discharge_disposition="SNF",
            source=SourceRef(page=quotes[2][1], quote=quotes[2][0], confidence=0.7),
        ),
    )


def test_grounds_exact_and_whitespace_insensitive():
    assert _grounds("DNR / DNI", "code status:  dnr / dni\nfull") is True
    assert _grounds("not in here", "totally different text") is False
    assert _grounds("", "anything") is False


def test_collect_sources_finds_all_three():
    chart = _chart({"a": 1, "b": 1, "c": 1})
    sources = _collect_sources(chart)
    paths = {p for p, _ in sources}
    assert paths == {"demographics.source", "insurance.source", "encounter.source"}


def test_verify_chart_flags_ungrounded():
    chart = _chart({"jane doe": 1, "medicare part a": 1, "ghost fact": 1})
    page_texts = ["Patient: Jane Doe, Medicare Part A coverage."]

    results = {r.field: r for r in verify_chart(chart, page_texts)}

    assert results["demographics.source"].grounded is True
    assert results["insurance.source"].grounded is True
    assert results["encounter.source"].grounded is False


def test_verify_chart_handles_out_of_range_page():
    chart = _chart({"jane doe": 99, "x": 1, "y": 1})
    results = {r.field: r for r in verify_chart(chart, ["page one text"])}
    assert results["demographics.source"].grounded is False
