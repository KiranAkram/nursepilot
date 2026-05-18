from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from .common import SourceRef


class ContactPerson(BaseModel):
    name: str
    relationship: str
    phone: str | None = None


class Demographics(BaseModel):
    family_name: str
    given_name: str
    dob: date
    gender: Literal["male", "female", "other", "unknown"]
    mrn: str
    ssn_last4: str | None = None
    address: str | None = None
    phone: str | None = None
    language: str = "English"
    language_preferred: str | None = None
    marital_status: str | None = None
    race: str | None = None
    ethnicity: str | None = None
    occupation: str | None = None
    dependents: str | None = None
    contacts: list[ContactPerson] = Field(default_factory=list)
    source: SourceRef


class Insurance(BaseModel):
    coverage_type: str                              # "Medicare Part A", "Union Health Plan"
    subscriber_id: str | None = None
    plan: str | None = None
    payor: str | None = None
    snf_days_remaining: int | None = None
    secondary_type: str | None = None
    secondary_subscriber_id: str | None = None
    preauth_number: str | None = None
    preauth_days: int | None = None
    workers_comp: str | None = None                 # "Filed — Liberty Mutual Policy #..."
    source: SourceRef


class Encounter(BaseModel):
    status: str                                     # "finished"
    encounter_class: str                            # "IMP (inpatient)"
    admit_start: datetime
    discharge_end: datetime
    admit_source: str | None = None                 # "Emergency Department"
    discharge_disposition: str                      # "SNF"
    reason_code: str | None = None
    length_days: int | None = None
    service_provider: str | None = None
    source: SourceRef


class Diagnosis(BaseModel):
    icd10_code: str
    description: str
    category: Literal["encounter-diagnosis", "problem-list-item"]
    onset: str | None = None                        # partial dates ok: "2019-04"
    status: str = "active"                          # "active", "resolved", "active (wound healing)"
    source: SourceRef


class Procedure(BaseModel):
    code: str | None = None                         # optional: some tables list by name only
    description: str
    status: Literal["completed", "in-progress", "planned"] = "completed"
    performed_datetime: datetime | None = None
    performed_date_label: str | None = None         # "11/22", "11/23-11/28" — narrative date ranges
    performer: str | None = None
    outcome: str | None = None
    note: str | None = None
    follow_up: str | None = None
    complication: str | None = None
    source: SourceRef


class Medication(BaseModel):
    name: str
    dose: str
    route: str
    frequency: str
    status: str                                     # "Active", "Active - NEW", "Active - TAPER", etc.
    indication: str | None = None
    source: SourceRef


class Allergy(BaseModel):
    substance: str
    reaction: str | None = None
    criticality: Literal["high", "low", "unknown"] = "unknown"
    allergy_type: Literal["allergy", "intolerance"] = "allergy"
    note: str | None = None
    source: SourceRef


class LabResult(BaseModel):
    test: str                                       # "WBC", "WBC (peak)", "Cr (peak during AKI)"
    result: str                                     # "<0.04", "Clear, WBC neg", "MSSA — susceptibility on file"
    units: str | None = None
    reference_range: str | None = None
    flag: Literal["HIGH", "LOW", "CRITICAL"] | None = None


class LabReport(BaseModel):
    specimen_datetime: datetime | None = None
    status: str = "final"
    performing_lab: str | None = None
    results: list[LabResult] = Field(default_factory=list)
    source: SourceRef


class ImagingReport(BaseModel):
    code: str                                       # "Chest X-Ray PA/Lat", "MRI Brain with DWI"
    effective_date: date | None = None
    conclusion: str
    source: SourceRef


class VitalSigns(BaseModel):
    bp: str | None = None                           # "132/82 mmHg"
    hr: str | None = None                           # "68 bpm, irregularly irregular"
    temp_f: float | None = None
    rr: str | None = None
    spo2: str | None = None
    weight_lbs: float | None = None
    height: str | None = None
    bmi: float | None = None
    pain: str | None = None
    admission_weight_lbs: float | None = None
    weight_loss: str | None = None                  # "-27 lbs (12.3 kg) over 31 days"
    net_fluid_loss: str | None = None
    dry_weight_target: str | None = None
    edema: str | None = None
    # neuro-specific (stroke, TBI)
    nihss_admission: str | None = None
    nihss_discharge: str | None = None
    mrs_discharge: str | None = None                # "4 (moderately severe disability)"
    observed_datetime: datetime | None = None
    source: SourceRef


class WoundAssessment(BaseModel):
    location: str
    description: str
    measurements: str | None = None                 # "Length x Width x Depth"
    stage: str | None = None
    drainage: str | None = None
    treatment: str | None = None
    source: SourceRef


class DischargeOrder(BaseModel):
    order: str                                      # "Physical Therapy"
    detail: str
    frequency: str | None = None
    duration: str | None = None


class FunctionalStatus(BaseModel):
    bims_score: str | None = None
    braden_scale: int | None = None
    phq9_score: str | None = None
    fall_risk_morse: int | None = None
    prior_functional_level: str | None = None
    gg_codes: dict[str, str] = Field(default_factory=dict)
    source: SourceRef


class Practitioner(BaseModel):
    role: str                                       # "Attending", "Surgeon", "PCP"
    name: str
    specialty: str | None = None
    npi: str | None = None
    phone: str | None = None


class Organization(BaseModel):
    role: Literal["sending", "receiving"]
    name: str
    org_type: str                                   # "Acute Care Hospital", "Skilled Nursing Facility"
    npi: str | None = None
    address: str | None = None


class AdvanceDirective(BaseModel):
    code_status: str                                # "FULL CODE", "DNR / DNI"
    polst_on_file: bool = False
    healthcare_poa_name: str | None = None
    poa_contact: str | None = None
    living_will: bool = False
    organ_donor: bool = False
    source: SourceRef


class CriticalAlert(BaseModel):
    severity: Literal["alert", "critical"] = "alert"
    message: str                                    # "Daily weights required — call MD if weight gain >2 lbs/day"
    source: SourceRef


class DischargeSummary(BaseModel):
    document_type: str = "18842-5"
    discharge_date: date | None = None
    author: str | None = None
    status: str = "current"
    narrative: str
    source: SourceRef


class PatientChart(BaseModel):
    demographics: Demographics
    insurance: Insurance
    encounter: Encounter
    clinical_history: str | None = None             # free-text narrative before/within conditions
    diagnoses: list[Diagnosis] = Field(default_factory=list)
    procedures: list[Procedure] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    pharmacy_notes: str | None = None
    allergies: list[Allergy] = Field(default_factory=list)
    lab_report: LabReport | None = None
    imaging_reports: list[ImagingReport] = Field(default_factory=list)
    vital_signs: VitalSigns | None = None
    wound_assessments: list[WoundAssessment] = Field(default_factory=list)
    discharge_orders: list[DischargeOrder] = Field(default_factory=list)
    alerts: list[CriticalAlert] = Field(default_factory=list)
    functional_status: FunctionalStatus | None = None
    practitioners: list[Practitioner] = Field(default_factory=list)
    organizations: list[Organization] = Field(default_factory=list)
    advance_directive: AdvanceDirective | None = None
    discharge_summary: DischargeSummary | None = None
