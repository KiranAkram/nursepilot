from datetime import date, datetime

import pytest
from pydantic import ValidationError

from schemas.common import SourceRef
from schemas.patient_chart import (
    Allergy,
    CriticalAlert,
    Demographics,
    Diagnosis,
    Encounter,
    Insurance,
    LabResult,
    Organization,
    PatientChart,
    Procedure,
)


def src(**overrides) -> dict:
    return {"page": 1, "quote": "sample extract", "confidence": 0.95, **overrides}


# ---------------------------------------------------------------------------
# SourceRef
# ---------------------------------------------------------------------------

def test_source_ref_valid():
    ref = SourceRef(page=3, quote="Patient admitted via ED", confidence=0.92)
    assert ref.page == 3
    assert ref.confidence == 0.92


@pytest.mark.parametrize("field", ["page", "quote", "confidence"])
def test_source_ref_missing_required(field):
    data = {"page": 1, "quote": "text", "confidence": 0.9}
    del data[field]
    with pytest.raises(ValidationError):
        SourceRef(**data)


# ---------------------------------------------------------------------------
# Demographics
# ---------------------------------------------------------------------------

def test_demographics_valid():
    d = Demographics(
        family_name="Smith",
        given_name="Jane",
        dob=date(1945, 3, 15),
        gender="female",
        mrn="MRN-001234",
        source=SourceRef(**src()),
    )
    assert d.language == "English"
    assert d.contacts == []


@pytest.mark.parametrize("gender", ["F", "M", "Woman", ""])
def test_demographics_invalid_gender(gender):
    with pytest.raises(ValidationError):
        Demographics(
            family_name="Smith", given_name="Jane",
            dob=date(1945, 3, 15), gender=gender,
            mrn="MRN-001234", source=SourceRef(**src()),
        )


def test_demographics_invalid_dob():
    with pytest.raises(ValidationError):
        Demographics(
            family_name="Smith", given_name="Jane",
            dob="not-a-date", gender="female",
            mrn="MRN-001234", source=SourceRef(**src()),
        )


@pytest.mark.parametrize("field", ["family_name", "given_name", "dob", "gender", "mrn", "source"])
def test_demographics_missing_required(field):
    data = dict(
        family_name="Smith", given_name="Jane",
        dob=date(1945, 3, 15), gender="female",
        mrn="MRN-001234", source=src(),
    )
    del data[field]
    with pytest.raises(ValidationError):
        Demographics(**data)


# ---------------------------------------------------------------------------
# Insurance
# ---------------------------------------------------------------------------

def test_insurance_valid():
    ins = Insurance(coverage_type="Medicare Part A", source=SourceRef(**src()))
    assert ins.subscriber_id is None
    assert ins.snf_days_remaining is None


def test_insurance_missing_coverage_type():
    with pytest.raises(ValidationError):
        Insurance(source=SourceRef(**src()))


# ---------------------------------------------------------------------------
# Encounter
# ---------------------------------------------------------------------------

def test_encounter_valid():
    enc = Encounter(
        status="finished",
        encounter_class="IMP (inpatient)",
        admit_start=datetime(2024, 11, 1, 8, 0),
        discharge_end=datetime(2024, 11, 10, 14, 0),
        discharge_disposition="SNF",
        source=SourceRef(**src()),
    )
    assert enc.length_days is None
    assert enc.admit_source is None


# ---------------------------------------------------------------------------
# Diagnosis
# ---------------------------------------------------------------------------

def test_diagnosis_valid():
    dx = Diagnosis(
        icd10_code="S72.141A",
        description="Displaced intertrochanteric fracture of right femur",
        category="encounter-diagnosis",
        source=SourceRef(**src()),
    )
    assert dx.status == "active"


@pytest.mark.parametrize("category", ["secondary", "primary", ""])
def test_diagnosis_invalid_category(category):
    with pytest.raises(ValidationError):
        Diagnosis(
            icd10_code="S72.141A",
            description="Hip fracture",
            category=category,
            source=SourceRef(**src()),
        )


# ---------------------------------------------------------------------------
# Procedure
# ---------------------------------------------------------------------------

def test_procedure_valid():
    p = Procedure(description="ORIF right hip", source=SourceRef(**src()))
    assert p.status == "completed"
    assert p.code is None


@pytest.mark.parametrize("status", ["cancelled", "pending", "done"])
def test_procedure_invalid_status(status):
    with pytest.raises(ValidationError):
        Procedure(description="ORIF", status=status, source=SourceRef(**src()))


# ---------------------------------------------------------------------------
# Allergy
# ---------------------------------------------------------------------------

def test_allergy_valid():
    a = Allergy(substance="Penicillin", source=SourceRef(**src()))
    assert a.criticality == "unknown"
    assert a.allergy_type == "allergy"
    assert a.reaction is None


@pytest.mark.parametrize("field,value", [
    ("criticality", "medium"),
    ("criticality", "severe"),
    ("allergy_type", "sensitivity"),
    ("allergy_type", "reaction"),
])
def test_allergy_invalid_literal(field, value):
    with pytest.raises(ValidationError):
        Allergy(substance="Penicillin", source=src(), **{field: value})


# ---------------------------------------------------------------------------
# LabResult
# ---------------------------------------------------------------------------

def test_lab_result_valid():
    lr = LabResult(test="WBC", result="11.2", units="K/uL", flag="HIGH")
    assert lr.flag == "HIGH"


def test_lab_result_no_flag():
    lr = LabResult(test="Na", result="138", units="mEq/L")
    assert lr.flag is None


@pytest.mark.parametrize("flag", ["ABNORMAL", "NORMAL", "H", "L"])
def test_lab_result_invalid_flag(flag):
    with pytest.raises(ValidationError):
        LabResult(test="WBC", result="11.2", flag=flag)


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------

def test_organization_valid():
    org = Organization(role="sending", name="City General Hospital", org_type="Acute Care Hospital")
    assert org.npi is None


@pytest.mark.parametrize("role", ["referring", "hospital", ""])
def test_organization_invalid_role(role):
    with pytest.raises(ValidationError):
        Organization(role=role, name="City General Hospital", org_type="Acute Care Hospital")


# ---------------------------------------------------------------------------
# CriticalAlert
# ---------------------------------------------------------------------------

def test_critical_alert_valid():
    alert = CriticalAlert(
        severity="critical",
        message="Daily weights — call MD if >2 lbs/day gain",
        source=SourceRef(**src()),
    )
    assert alert.severity == "critical"


@pytest.mark.parametrize("severity", ["warning", "info", "high"])
def test_critical_alert_invalid_severity(severity):
    with pytest.raises(ValidationError):
        CriticalAlert(severity=severity, message="msg", source=src())


# ---------------------------------------------------------------------------
# PatientChart — minimal valid + missing required fields
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_chart_data() -> dict:
    s = src()
    return {
        "demographics": {
            "family_name": "Smith", "given_name": "Jane",
            "dob": "1945-03-15", "gender": "female",
            "mrn": "MRN-001234", "source": s,
        },
        "insurance": {"coverage_type": "Medicare Part A", "source": s},
        "encounter": {
            "status": "finished",
            "encounter_class": "IMP (inpatient)",
            "admit_start": "2024-11-01T08:00:00",
            "discharge_end": "2024-11-10T14:00:00",
            "discharge_disposition": "SNF",
            "source": s,
        },
    }


def test_patient_chart_minimal_valid(minimal_chart_data):
    chart = PatientChart.model_validate(minimal_chart_data)
    assert chart.demographics.family_name == "Smith"
    assert chart.diagnoses == []
    assert chart.medications == []
    assert chart.lab_report is None
    assert chart.advance_directive is None


@pytest.mark.parametrize("field", ["demographics", "insurance", "encounter"])
def test_patient_chart_missing_required(minimal_chart_data, field):
    del minimal_chart_data[field]
    with pytest.raises(ValidationError):
        PatientChart.model_validate(minimal_chart_data)


# ---------------------------------------------------------------------------
# Hip fracture fixture — realistic end-to-end validation
# ---------------------------------------------------------------------------

HIP_FRACTURE_CHART = {
    "demographics": {
        "family_name": "Martinez",
        "given_name": "Eleanor",
        "dob": "1942-07-22",
        "gender": "female",
        "mrn": "MRN-884412",
        "ssn_last4": "7823",
        "address": "412 Maple Avenue, Springfield, IL 62701",
        "phone": "217-555-0193",
        "marital_status": "Widowed",
        "contacts": [{"name": "Robert Martinez", "relationship": "Son", "phone": "217-555-0247"}],
        "source": {"page": 1, "quote": "Patient: Eleanor Martinez DOB: 07/22/1942", "confidence": 0.98},
    },
    "insurance": {
        "coverage_type": "Medicare Part A",
        "subscriber_id": "1EG4-TE5-MK72",
        "snf_days_remaining": 100,
        "secondary_type": "AARP Supplemental",
        "source": {"page": 2, "quote": "Insurance: Medicare Part A Subscriber ID: 1EG4-TE5-MK72", "confidence": 0.97},
    },
    "encounter": {
        "status": "finished",
        "encounter_class": "IMP (inpatient)",
        "admit_start": "2024-11-01T09:30:00",
        "discharge_end": "2024-11-10T14:00:00",
        "admit_source": "Emergency Department",
        "discharge_disposition": "SNF",
        "reason_code": "Fall resulting in hip fracture",
        "length_days": 9,
        "service_provider": "Springfield General Hospital",
        "source": {"page": 2, "quote": "Admitted: 11/01/2024 Discharged: 11/10/2024", "confidence": 0.99},
    },
    "diagnoses": [
        {
            "icd10_code": "S72.141A",
            "description": "Displaced intertrochanteric fracture of right femur, initial encounter",
            "category": "encounter-diagnosis",
            "onset": "2024-11-01",
            "status": "active",
            "source": {"page": 3, "quote": "S72.141A — Displaced intertrochanteric fracture right femur", "confidence": 0.97},
        },
        {
            "icd10_code": "I10",
            "description": "Essential (primary) hypertension",
            "category": "problem-list-item",
            "status": "active",
            "source": {"page": 4, "quote": "Hypertension — ongoing", "confidence": 0.93},
        },
    ],
    "procedures": [
        {
            "code": "27236",
            "description": "Open reduction and internal fixation (ORIF) of right hip",
            "status": "completed",
            "performed_datetime": "2024-11-02T07:45:00",
            "performer": "Dr. Alan Chen, MD — Orthopedic Surgery",
            "outcome": "Procedure completed without complication",
            "source": {"page": 5, "quote": "ORIF right hip 11/02/2024 — Dr. Alan Chen", "confidence": 0.98},
        },
    ],
    "medications": [
        {
            "name": "Enoxaparin (Lovenox)",
            "dose": "40 mg",
            "route": "Subcutaneous",
            "frequency": "Daily",
            "status": "Active",
            "indication": "DVT prophylaxis post-op",
            "source": {"page": 6, "quote": "Enoxaparin 40 mg SC daily — DVT prophylaxis", "confidence": 0.97},
        },
        {
            "name": "Oxycodone/Acetaminophen",
            "dose": "5/325 mg",
            "route": "Oral",
            "frequency": "Every 6 hours PRN",
            "status": "Active",
            "indication": "Pain management",
            "source": {"page": 6, "quote": "Oxycodone/APAP 5/325 mg PO q6h PRN pain", "confidence": 0.96},
        },
        {
            "name": "Lisinopril",
            "dose": "10 mg",
            "route": "Oral",
            "frequency": "Daily",
            "status": "Active",
            "indication": "Hypertension",
            "source": {"page": 6, "quote": "Lisinopril 10 mg PO daily", "confidence": 0.95},
        },
    ],
    "allergies": [
        {
            "substance": "Penicillin",
            "reaction": "Rash, urticaria",
            "criticality": "high",
            "allergy_type": "allergy",
            "source": {"page": 2, "quote": "Allergy: Penicillin — rash/urticaria", "confidence": 0.98},
        },
    ],
    "lab_report": {
        "specimen_datetime": "2024-11-09T06:15:00",
        "status": "final",
        "performing_lab": "Springfield General Hospital Laboratory",
        "results": [
            {"test": "Hgb", "result": "9.8", "units": "g/dL", "reference_range": "12.0-16.0", "flag": "LOW"},
            {"test": "WBC", "result": "8.4", "units": "K/uL", "reference_range": "4.5-11.0"},
            {"test": "Cr", "result": "1.1", "units": "mg/dL", "reference_range": "0.6-1.2"},
        ],
        "source": {"page": 7, "quote": "CBC/BMP drawn 11/09/2024 06:15", "confidence": 0.96},
    },
    "vital_signs": {
        "bp": "128/76 mmHg",
        "hr": "72 bpm",
        "temp_f": 98.4,
        "rr": "16/min",
        "spo2": "97% on room air",
        "weight_lbs": 142.0,
        "height": "5'4\"",
        "bmi": 24.4,
        "pain": "3/10",
        "observed_datetime": "2024-11-10T07:00:00",
        "source": {"page": 8, "quote": "Vitals 11/10/2024 07:00 — BP 128/76", "confidence": 0.99},
    },
    "discharge_orders": [
        {"order": "Physical Therapy", "detail": "Gait training, hip precautions", "frequency": "Daily", "duration": "6 weeks"},
        {"order": "Occupational Therapy", "detail": "ADL retraining", "frequency": "Daily", "duration": "4 weeks"},
        {"order": "Wound Care", "detail": "Staple removal at 14 days post-op", "frequency": "Daily"},
    ],
    "functional_status": {
        "braden_scale": 18,
        "fall_risk_morse": 55,
        "prior_functional_level": "Independent in all ADLs prior to fall",
        "gg_codes": {"GG0130A1": "03", "GG0130B1": "02"},
        "source": {"page": 9, "quote": "Braden Scale: 18 | Morse Fall Risk: 55", "confidence": 0.94},
    },
    "practitioners": [
        {"role": "Attending", "name": "Dr. Sarah Okonkwo, MD", "specialty": "Internal Medicine", "npi": "1234567890"},
        {"role": "Surgeon", "name": "Dr. Alan Chen, MD", "specialty": "Orthopedic Surgery", "npi": "0987654321"},
    ],
    "organizations": [
        {"role": "sending", "name": "Springfield General Hospital", "org_type": "Acute Care Hospital", "npi": "1122334455"},
        {"role": "receiving", "name": "Sunrise Skilled Nursing & Rehab", "org_type": "Skilled Nursing Facility"},
    ],
    "advance_directive": {
        "code_status": "FULL CODE",
        "polst_on_file": False,
        "healthcare_poa_name": "Robert Martinez",
        "poa_contact": "217-555-0247",
        "living_will": False,
        "organ_donor": True,
        "source": {"page": 10, "quote": "Code Status: Full Code | POA: Robert Martinez", "confidence": 0.97},
    },
    "alerts": [
        {
            "severity": "alert",
            "message": "Hip precautions — no flexion >90°, no internal rotation",
            "source": {"page": 1, "quote": "ALERT: Hip precautions in effect", "confidence": 0.99},
        },
    ],
}


def test_hip_fracture_chart_validates():
    chart = PatientChart.model_validate(HIP_FRACTURE_CHART)

    assert chart.demographics.family_name == "Martinez"
    assert chart.demographics.dob == date(1942, 7, 22)
    assert len(chart.demographics.contacts) == 1

    assert chart.insurance.snf_days_remaining == 100

    assert chart.encounter.length_days == 9
    assert chart.encounter.admit_source == "Emergency Department"

    assert len(chart.diagnoses) == 2
    assert chart.diagnoses[0].icd10_code == "S72.141A"
    assert chart.diagnoses[1].category == "problem-list-item"

    assert len(chart.medications) == 3

    assert chart.lab_report is not None
    assert len(chart.lab_report.results) == 3
    assert chart.lab_report.results[0].flag == "LOW"
    assert chart.lab_report.results[1].flag is None

    assert chart.vital_signs is not None
    assert chart.vital_signs.temp_f == 98.4

    assert chart.functional_status is not None
    assert chart.functional_status.braden_scale == 18
    assert chart.functional_status.gg_codes["GG0130A1"] == "03"

    assert chart.advance_directive is not None
    assert chart.advance_directive.organ_donor is True

    assert len(chart.alerts) == 1
    assert chart.alerts[0].severity == "alert"

    assert chart.organizations[0].role == "sending"
    assert chart.organizations[1].role == "receiving"
