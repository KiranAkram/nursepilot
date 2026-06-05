// Mirrors shared/schemas/patient_chart.py. Keep in sync with the Pydantic models.

export interface SourceRef {
  page: number
  quote: string
  confidence: number
}

export interface ContactPerson {
  name: string
  relationship: string
  phone?: string | null
}

export interface Demographics {
  family_name: string
  given_name: string
  dob: string
  gender: "male" | "female" | "other" | "unknown"
  mrn: string
  ssn_last4?: string | null
  address?: string | null
  phone?: string | null
  language: string
  language_preferred?: string | null
  marital_status?: string | null
  race?: string | null
  ethnicity?: string | null
  occupation?: string | null
  dependents?: string | null
  contacts: ContactPerson[]
  source: SourceRef
}

export interface Insurance {
  coverage_type: string
  subscriber_id?: string | null
  plan?: string | null
  payor?: string | null
  snf_days_remaining?: number | null
  secondary_type?: string | null
  secondary_subscriber_id?: string | null
  preauth_number?: string | null
  preauth_days?: number | null
  workers_comp?: string | null
  source: SourceRef
}

export interface Encounter {
  status: string
  encounter_class: string
  admit_start: string
  discharge_end: string
  admit_source?: string | null
  discharge_disposition: string
  reason_code?: string | null
  length_days?: number | null
  service_provider?: string | null
  source: SourceRef
}

export interface Diagnosis {
  icd10_code: string
  description: string
  category: "encounter-diagnosis" | "problem-list-item"
  onset?: string | null
  status: string
  source: SourceRef
}

export interface Procedure {
  code?: string | null
  description: string
  status: "completed" | "in-progress" | "planned"
  performed_datetime?: string | null
  performed_date_label?: string | null
  performer?: string | null
  outcome?: string | null
  note?: string | null
  follow_up?: string | null
  complication?: string | null
  source: SourceRef
}

export interface Medication {
  name: string
  dose: string
  route: string
  frequency: string
  status: string
  indication?: string | null
  source: SourceRef
}

export interface Allergy {
  substance: string
  reaction?: string | null
  criticality: "high" | "low" | "unknown"
  allergy_type: "allergy" | "intolerance"
  note?: string | null
  source: SourceRef
}

export interface LabResult {
  test: string
  result: string
  units?: string | null
  reference_range?: string | null
  flag?: "HIGH" | "LOW" | "CRITICAL" | null
}

export interface LabReport {
  specimen_datetime?: string | null
  status: string
  performing_lab?: string | null
  results: LabResult[]
  source: SourceRef
}

export interface ImagingReport {
  code: string
  effective_date?: string | null
  conclusion: string
  source: SourceRef
}

export interface VitalSigns {
  bp?: string | null
  hr?: string | null
  temp_f?: number | null
  rr?: string | null
  spo2?: string | null
  weight_lbs?: number | null
  height?: string | null
  bmi?: number | null
  pain?: string | null
  admission_weight_lbs?: number | null
  weight_loss?: string | null
  net_fluid_loss?: string | null
  dry_weight_target?: string | null
  edema?: string | null
  nihss_admission?: string | null
  nihss_discharge?: string | null
  mrs_discharge?: string | null
  observed_datetime?: string | null
  source: SourceRef
}

export interface WoundAssessment {
  location: string
  description: string
  measurements?: string | null
  stage?: string | null
  drainage?: string | null
  treatment?: string | null
  source: SourceRef
}

export interface DischargeOrder {
  order: string
  detail: string
  frequency?: string | null
  duration?: string | null
}

export interface FunctionalStatus {
  bims_score?: string | null
  braden_scale?: number | null
  phq9_score?: string | null
  fall_risk_morse?: number | null
  prior_functional_level?: string | null
  gg_codes: Record<string, string>
  source: SourceRef
}

export interface Practitioner {
  role: string
  name: string
  specialty?: string | null
  npi?: string | null
  phone?: string | null
}

export interface Organization {
  role: "sending" | "receiving"
  name: string
  org_type: string
  npi?: string | null
  address?: string | null
}

export interface AdvanceDirective {
  code_status: string
  polst_on_file: boolean
  healthcare_poa_name?: string | null
  poa_contact?: string | null
  living_will: boolean
  organ_donor: boolean
  source: SourceRef
}

export interface CriticalAlert {
  severity: "alert" | "critical"
  message: string
  source: SourceRef
}

export interface DischargeSummary {
  document_type: string
  discharge_date?: string | null
  author?: string | null
  status: string
  narrative: string
  source: SourceRef
}

export interface PatientChart {
  demographics: Demographics
  insurance: Insurance
  encounter: Encounter
  clinical_history?: string | null
  diagnoses: Diagnosis[]
  procedures: Procedure[]
  medications: Medication[]
  pharmacy_notes?: string | null
  allergies: Allergy[]
  lab_report?: LabReport | null
  imaging_reports: ImagingReport[]
  vital_signs?: VitalSigns | null
  wound_assessments: WoundAssessment[]
  discharge_orders: DischargeOrder[]
  alerts: CriticalAlert[]
  functional_status?: FunctionalStatus | null
  practitioners: Practitioner[]
  organizations: Organization[]
  advance_directive?: AdvanceDirective | null
  discharge_summary?: DischargeSummary | null
}

// Mirrors worker/verification.py GroundingResult.
export interface GroundingResult {
  field: string // dotted path, e.g. "diagnoses[0].source"
  page: number
  grounded: boolean
  confidence: number
}

export type JobStatus =
  | { job_id: string; status: "processing" }
  | { job_id: string; status: "done"; chart: PatientChart; grounding: GroundingResult[] }
  | { job_id: string; status: "error"; detail: string }
