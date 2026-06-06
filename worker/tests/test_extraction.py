from datetime import date, datetime

import pytest
from pydantic import ValidationError

from extraction import extract_chart_from_pdf, validate_with_salvage
from schemas import PatientChart
from schemas.common import SourceRef
from schemas.patient_chart import Demographics, Encounter, Insurance


def _minimal_chart() -> PatientChart:
    src = SourceRef(page=1, quote="x", confidence=0.9)
    return PatientChart(
        demographics=Demographics(
            family_name="Doe",
            given_name="Jane",
            dob=date(1950, 1, 1),
            gender="female",
            mrn="MRN1",
            source=src,
        ),
        insurance=Insurance(coverage_type="Medicare Part A", source=src),
        encounter=Encounter(
            status="finished",
            encounter_class="IMP",
            admit_start=datetime(2024, 1, 1),
            discharge_end=datetime(2024, 1, 5),
            discharge_disposition="SNF",
            source=src,
        ),
    )


class _FakeResponse:
    def __init__(self, parsed):
        self.parsed = parsed
        self.text = parsed.model_dump_json()


class _FakeModels:
    def __init__(self, chart):
        self._chart = chart
        self.called_with = None

    def generate_content(self, **kwargs):
        self.called_with = kwargs
        return _FakeResponse(self._chart)


class _FakeClient:
    def __init__(self, chart):
        self.models = _FakeModels(chart)


def test_extract_returns_parsed_chart():
    chart = _minimal_chart()
    client = _FakeClient(chart)

    result, flagged = extract_chart_from_pdf(b"%PDF-fake", client=client, model="m")

    assert isinstance(result, PatientChart)
    assert result.demographics.mrn == "MRN1"
    assert flagged == []
    assert client.models.called_with["model"] == "m"


def test_extract_falls_back_to_json_when_parsed_missing():
    chart = _minimal_chart()
    client = _FakeClient(chart)
    client.models._chart = chart

    # parsed is a PatientChart here; simulate SDK returning non-model parsed
    class _NoParse(_FakeResponse):
        def __init__(self, parsed):
            super().__init__(parsed)
            self.parsed = None

    client.models.generate_content = lambda **kw: _NoParse(chart)

    result, _ = extract_chart_from_pdf(b"%PDF-fake", client=client)
    assert isinstance(result, PatientChart)
    assert result.encounter.discharge_disposition == "SNF"


def _minimal_chart_dict() -> dict:
    return _minimal_chart().model_dump(mode="json")


def test_salvage_quarantines_bad_optional_value():
    raw = _minimal_chart_dict()
    raw["allergies"] = [
        {
            "substance": "Penicillin",
            "criticality": "SUPER-HIGH",  # not a valid Literal
            "source": {"page": 1, "quote": "x", "confidence": 0.9},
        }
    ]

    chart, flagged = validate_with_salvage(raw)

    # rest of the chart survived; bad value dropped to its default and recorded
    assert chart.allergies[0].substance == "Penicillin"
    assert chart.allergies[0].criticality == "unknown"
    assert len(flagged) == 1
    assert flagged[0]["path"] == "allergies.0.criticality"
    assert flagged[0]["value"] == "SUPER-HIGH"


def test_salvage_clean_chart_has_no_flags():
    chart, flagged = validate_with_salvage(_minimal_chart_dict())
    assert isinstance(chart, PatientChart)
    assert flagged == []


def test_salvage_still_raises_on_bad_required_field():
    raw = _minimal_chart_dict()
    raw["demographics"]["gender"] = "bogus"  # required, no default — unsalvageable
    with pytest.raises(ValidationError):
        validate_with_salvage(raw)
