from datetime import date, datetime

from extraction import extract_chart_from_pdf
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

    result = extract_chart_from_pdf(b"%PDF-fake", client=client, model="m")

    assert isinstance(result, PatientChart)
    assert result.demographics.mrn == "MRN1"
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

    result = extract_chart_from_pdf(b"%PDF-fake", client=client)
    assert isinstance(result, PatientChart)
    assert result.encounter.discharge_disposition == "SNF"
