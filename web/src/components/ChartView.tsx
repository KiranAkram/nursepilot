import { AlertTriangle, ShieldAlert } from "lucide-react"
import type { ReactNode } from "react"

import { GroundingProvider } from "@/components/grounding"
import { SourceChip } from "@/components/SourceChip"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { TooltipProvider } from "@/components/ui/tooltip"
import type { GroundingResult, PatientChart, SourceRef } from "@/types/chart"

// ---------------------------------------------------------------------------
// Small presentational helpers
// ---------------------------------------------------------------------------

function age(dob: string): number | null {
  const d = new Date(dob)
  if (Number.isNaN(d.getTime())) return null
  const now = new Date()
  let a = now.getFullYear() - d.getFullYear()
  const m = now.getMonth() - d.getMonth()
  if (m < 0 || (m === 0 && now.getDate() < d.getDate())) a--
  return a
}

function fmtDate(value?: string | null): string {
  if (!value) return "—"
  const d = new Date(value)
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString()
}

function Field({
  label,
  value,
  source,
  path,
}: {
  label: string
  value: ReactNode
  source?: SourceRef
  path?: string
}) {
  if (value === null || value === undefined || value === "") return null
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="flex items-center gap-2 text-sm">
        {value}
        {source && path && <SourceChip source={source} path={path} />}
      </span>
    </div>
  )
}

function Section({ title, count, children }: { title: string; count?: number; children: ReactNode }) {
  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle>{title}</CardTitle>
        {count !== undefined && <Badge variant="secondary">{count}</Badge>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

function Empty({ label }: { label: string }) {
  return <p className="text-sm text-muted-foreground">No {label} recorded.</p>
}

function Th({ children }: { children: ReactNode }) {
  return (
    <th className="border-b px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
      {children}
    </th>
  )
}

function Td({ children }: { children: ReactNode }) {
  return <td className="border-b px-3 py-2 align-top text-sm">{children}</td>
}

// ---------------------------------------------------------------------------
// Banner
// ---------------------------------------------------------------------------

function Banner({ chart }: { chart: PatientChart }) {
  const d = chart.demographics
  const a = age(d.dob)
  const code = chart.advance_directive?.code_status
  return (
    <Card className="border-l-4 border-l-primary">
      <CardContent className="flex flex-wrap items-center gap-x-8 gap-y-3 p-4">
        <div>
          <div className="flex items-center gap-2 text-xl font-semibold">
            {d.family_name}, {d.given_name}
            <SourceChip source={d.source} path="demographics.source" />
          </div>
          <div className="text-sm text-muted-foreground">
            MRN {d.mrn} · {a !== null ? `${a}y ` : ""}
            {d.gender} · DOB {fmtDate(d.dob)}
          </div>
        </div>
        <Separator orientation="vertical" className="h-10" />
        <div className="flex flex-wrap items-center gap-2">
          {code && (
            <Badge variant={code.toUpperCase().includes("DNR") ? "destructive" : "outline"}>
              {code}
            </Badge>
          )}
          {chart.allergies.map((al, i) => (
            <Badge key={i} variant="warning" title={al.reaction ?? undefined}>
              <ShieldAlert className="mr-1 !size-3" />
              {al.substance}
            </Badge>
          ))}
          {chart.allergies.length === 0 && <Badge variant="secondary">NKDA</Badge>}
        </div>
      </CardContent>
    </Card>
  )
}

function Alerts({ chart }: { chart: PatientChart }) {
  if (chart.alerts.length === 0) return null
  return (
    <div className="space-y-2">
      {chart.alerts.map((alert, i) => (
        <div
          key={i}
          className={
            "flex items-start gap-2 rounded-lg border p-3 text-sm " +
            (alert.severity === "critical"
              ? "border-destructive/30 bg-destructive/10 text-destructive"
              : "border-amber-300 bg-amber-50 text-amber-800")
          }
        >
          <AlertTriangle className="mt-0.5 !size-4 shrink-0" />
          <span className="flex-1">{alert.message}</span>
          <SourceChip source={alert.source} path={`alerts[${i}].source`} />
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sections
// ---------------------------------------------------------------------------

function Overview({ chart }: { chart: PatientChart }) {
  const { encounter: e, insurance: ins } = chart
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Section title="Encounter">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Class" value={e.encounter_class} />
          <Field label="Disposition" value={e.discharge_disposition} />
          <Field label="Admitted" value={fmtDate(e.admit_start)} />
          <Field label="Discharged" value={fmtDate(e.discharge_end)} />
          <Field label="Admit source" value={e.admit_source} />
          <Field label="Length (days)" value={e.length_days} />
          <Field label="Reason" value={e.reason_code} source={e.source} path="encounter.source" />
        </div>
      </Section>
      <Section title="Insurance">
        <div className="grid grid-cols-2 gap-3">
          <Field label="Coverage" value={ins.coverage_type} />
          <Field label="Subscriber ID" value={ins.subscriber_id} />
          <Field label="Plan" value={ins.plan} />
          <Field label="SNF days left" value={ins.snf_days_remaining} />
          <Field label="Secondary" value={ins.secondary_type} />
          <Field
            label="Preauth"
            value={ins.preauth_number}
            source={ins.source}
            path="insurance.source"
          />
        </div>
      </Section>
      {chart.clinical_history && (
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Clinical History</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm">{chart.clinical_history}</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

function Diagnoses({ chart }: { chart: PatientChart }) {
  return (
    <Section title="Diagnoses" count={chart.diagnoses.length}>
      {chart.diagnoses.length === 0 ? (
        <Empty label="diagnoses" />
      ) : (
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>ICD-10</Th>
              <Th>Description</Th>
              <Th>Category</Th>
              <Th>Status</Th>
              <Th>Source</Th>
            </tr>
          </thead>
          <tbody>
            {chart.diagnoses.map((dx, i) => (
              <tr key={i}>
                <Td>
                  <span className="font-mono">{dx.icd10_code}</span>
                </Td>
                <Td>{dx.description}</Td>
                <Td>
                  <Badge variant="outline">{dx.category}</Badge>
                </Td>
                <Td>{dx.status}</Td>
                <Td>
                  <SourceChip source={dx.source} path={`diagnoses[${i}].source`} />
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Section>
  )
}

function Medications({ chart }: { chart: PatientChart }) {
  return (
    <Section title="Medications" count={chart.medications.length}>
      {chart.medications.length === 0 ? (
        <Empty label="medications" />
      ) : (
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Medication</Th>
              <Th>Dose</Th>
              <Th>Route</Th>
              <Th>Frequency</Th>
              <Th>Status</Th>
              <Th>Indication</Th>
              <Th>Source</Th>
            </tr>
          </thead>
          <tbody>
            {chart.medications.map((m, i) => (
              <tr key={i}>
                <Td>
                  <span className="font-medium">{m.name}</span>
                </Td>
                <Td>{m.dose}</Td>
                <Td>{m.route}</Td>
                <Td>{m.frequency}</Td>
                <Td>{m.status}</Td>
                <Td>{m.indication ?? "—"}</Td>
                <Td>
                  <SourceChip source={m.source} path={`medications[${i}].source`} />
                </Td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {chart.pharmacy_notes && (
        <p className="mt-3 text-sm text-muted-foreground">
          <span className="font-medium text-foreground">Pharmacy notes: </span>
          {chart.pharmacy_notes}
        </p>
      )}
    </Section>
  )
}

const FLAG_TONE: Record<string, "destructive" | "warning"> = {
  CRITICAL: "destructive",
  HIGH: "warning",
  LOW: "warning",
}

function Labs({ chart }: { chart: PatientChart }) {
  const lab = chart.lab_report
  return (
    <Section title="Laboratory" count={lab?.results.length}>
      {!lab ? (
        <Empty label="lab results" />
      ) : (
        <>
          <div className="mb-3 flex flex-wrap gap-4 text-sm text-muted-foreground">
            <span>Collected {fmtDate(lab.specimen_datetime)}</span>
            {lab.performing_lab && <span>{lab.performing_lab}</span>}
            <SourceChip source={lab.source} path="lab_report.source" />
          </div>
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <Th>Test</Th>
                <Th>Result</Th>
                <Th>Units</Th>
                <Th>Reference</Th>
                <Th>Flag</Th>
              </tr>
            </thead>
            <tbody>
              {lab.results.map((r, i) => (
                <tr key={i}>
                  <Td>{r.test}</Td>
                  <Td>
                    <span className="font-medium">{r.result}</span>
                  </Td>
                  <Td>{r.units ?? "—"}</Td>
                  <Td>{r.reference_range ?? "—"}</Td>
                  <Td>{r.flag && <Badge variant={FLAG_TONE[r.flag]}>{r.flag}</Badge>}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </Section>
  )
}

function Procedures({ chart }: { chart: PatientChart }) {
  return (
    <Section title="Procedures" count={chart.procedures.length}>
      {chart.procedures.length === 0 ? (
        <Empty label="procedures" />
      ) : (
        <div className="space-y-3">
          {chart.procedures.map((p, i) => (
            <div key={i} className="rounded-lg border p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{p.description}</span>
                <SourceChip source={p.source} path={`procedures[${i}].source`} />
              </div>
              <div className="mt-1 text-sm text-muted-foreground">
                {[p.code && `Code ${p.code}`, p.status, p.performer, p.performed_date_label ?? fmtDate(p.performed_datetime)]
                  .filter(Boolean)
                  .join(" · ")}
              </div>
              {p.outcome && <p className="mt-1 text-sm">{p.outcome}</p>}
              {p.complication && (
                <p className="mt-1 text-sm text-destructive">Complication: {p.complication}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}

function Imaging({ chart }: { chart: PatientChart }) {
  return (
    <Section title="Imaging" count={chart.imaging_reports.length}>
      {chart.imaging_reports.length === 0 ? (
        <Empty label="imaging" />
      ) : (
        <div className="space-y-3">
          {chart.imaging_reports.map((img, i) => (
            <div key={i} className="rounded-lg border p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium">{img.code}</span>
                <SourceChip source={img.source} path={`imaging_reports[${i}].source`} />
              </div>
              <div className="text-xs text-muted-foreground">{fmtDate(img.effective_date)}</div>
              <p className="mt-1 text-sm">{img.conclusion}</p>
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}

function Vitals({ chart }: { chart: PatientChart }) {
  const v = chart.vital_signs
  if (!v) return <Section title="Vitals"><Empty label="vitals" /></Section>
  return (
    <Section title="Vital Signs">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <Field label="BP" value={v.bp} />
        <Field label="HR" value={v.hr} />
        <Field label="Temp °F" value={v.temp_f} />
        <Field label="RR" value={v.rr} />
        <Field label="SpO₂" value={v.spo2} />
        <Field label="Weight (lbs)" value={v.weight_lbs} />
        <Field label="BMI" value={v.bmi} />
        <Field label="Pain" value={v.pain} />
        <Field label="Edema" value={v.edema} />
        <Field label="Weight loss" value={v.weight_loss} />
        <Field label="NIHSS (d/c)" value={v.nihss_discharge} />
        <Field label="mRS (d/c)" value={v.mrs_discharge} source={v.source} path="vital_signs.source" />
      </div>
    </Section>
  )
}

function Wounds({ chart }: { chart: PatientChart }) {
  if (chart.wound_assessments.length === 0) return null
  return (
    <Section title="Wounds" count={chart.wound_assessments.length}>
      <div className="space-y-3">
        {chart.wound_assessments.map((w, i) => (
          <div key={i} className="rounded-lg border p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">{w.location}</span>
              <SourceChip source={w.source} path={`wound_assessments[${i}].source`} />
            </div>
            <p className="mt-1 text-sm">{w.description}</p>
            <div className="mt-1 text-sm text-muted-foreground">
              {[w.stage, w.measurements, w.drainage, w.treatment].filter(Boolean).join(" · ")}
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}

function Functional({ chart }: { chart: PatientChart }) {
  const f = chart.functional_status
  return (
    <Section title="Functional Status">
      {!f ? (
        <Empty label="functional status" />
      ) : (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Field label="BIMS" value={f.bims_score} />
            <Field label="Braden" value={f.braden_scale} />
            <Field label="PHQ-9" value={f.phq9_score} />
            <Field label="Morse fall risk" value={f.fall_risk_morse} />
            <Field
              label="Prior level"
              value={f.prior_functional_level}
              source={f.source}
              path="functional_status.source"
            />
          </div>
          {Object.keys(f.gg_codes).length > 0 && (
            <div className="flex flex-wrap gap-1">
              {Object.entries(f.gg_codes).map(([k, val]) => (
                <Badge key={k} variant="outline">
                  {k}: {val}
                </Badge>
              ))}
            </div>
          )}
        </div>
      )}
    </Section>
  )
}

function Discharge({ chart }: { chart: PatientChart }) {
  return (
    <div className="space-y-4">
      <Section title="Discharge Orders" count={chart.discharge_orders.length}>
        {chart.discharge_orders.length === 0 ? (
          <Empty label="orders" />
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <Th>Order</Th>
                <Th>Detail</Th>
                <Th>Frequency</Th>
                <Th>Duration</Th>
              </tr>
            </thead>
            <tbody>
              {chart.discharge_orders.map((o, i) => (
                <tr key={i}>
                  <Td>
                    <span className="font-medium">{o.order}</span>
                  </Td>
                  <Td>{o.detail}</Td>
                  <Td>{o.frequency ?? "—"}</Td>
                  <Td>{o.duration ?? "—"}</Td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>
      {chart.discharge_summary && (
        <Section title="Discharge Summary">
          <div className="mb-2 flex items-center gap-2 text-sm text-muted-foreground">
            {chart.discharge_summary.author && <span>{chart.discharge_summary.author}</span>}
            <span>{fmtDate(chart.discharge_summary.discharge_date)}</span>
            <SourceChip source={chart.discharge_summary.source} path="discharge_summary.source" />
          </div>
          <p className="whitespace-pre-wrap text-sm">{chart.discharge_summary.narrative}</p>
        </Section>
      )}
    </div>
  )
}

function CareTeam({ chart }: { chart: PatientChart }) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Section title="Practitioners" count={chart.practitioners.length}>
        {chart.practitioners.length === 0 ? (
          <Empty label="practitioners" />
        ) : (
          <ul className="space-y-2">
            {chart.practitioners.map((p, i) => (
              <li key={i} className="text-sm">
                <span className="font-medium">{p.name}</span>
                <span className="text-muted-foreground">
                  {" "}
                  — {[p.role, p.specialty, p.phone].filter(Boolean).join(" · ")}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>
      <Section title="Organizations" count={chart.organizations.length}>
        {chart.organizations.length === 0 ? (
          <Empty label="organizations" />
        ) : (
          <ul className="space-y-2">
            {chart.organizations.map((o, i) => (
              <li key={i} className="text-sm">
                <Badge variant="outline" className="mr-2">
                  {o.role}
                </Badge>
                <span className="font-medium">{o.name}</span>
                <span className="text-muted-foreground"> — {o.org_type}</span>
              </li>
            ))}
          </ul>
        )}
      </Section>
      {chart.advance_directive && (
        <Section title="Advance Directive">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Code status" value={chart.advance_directive.code_status} />
            <Field label="POLST on file" value={chart.advance_directive.polst_on_file ? "Yes" : "No"} />
            <Field label="Healthcare POA" value={chart.advance_directive.healthcare_poa_name} />
            <Field
              label="Organ donor"
              value={chart.advance_directive.organ_donor ? "Yes" : "No"}
              source={chart.advance_directive.source}
              path="advance_directive.source"
            />
          </div>
        </Section>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Grounding summary + root
// ---------------------------------------------------------------------------

function GroundingSummary({ grounding }: { grounding: GroundingResult[] }) {
  if (grounding.length === 0) return null
  const grounded = grounding.filter((g) => g.grounded).length
  const pct = Math.round((grounded / grounding.length) * 100)
  return (
    <Badge variant={pct >= 80 ? "success" : "warning"}>
      {grounded}/{grounding.length} facts grounded ({pct}%)
    </Badge>
  )
}

const TABS = [
  { value: "overview", label: "Overview", render: Overview },
  { value: "diagnoses", label: "Diagnoses", render: Diagnoses },
  { value: "medications", label: "Medications", render: Medications },
  { value: "labs", label: "Labs", render: Labs },
  { value: "imaging", label: "Imaging", render: Imaging },
  { value: "procedures", label: "Procedures", render: Procedures },
  { value: "vitals", label: "Vitals", render: Vitals },
  { value: "functional", label: "Functional", render: Functional },
  { value: "discharge", label: "Discharge", render: Discharge },
  { value: "team", label: "Care Team", render: CareTeam },
] as const

export function ChartView({
  chart,
  grounding,
}: {
  chart: PatientChart
  grounding: GroundingResult[]
}) {
  return (
    <TooltipProvider delayDuration={150}>
      <GroundingProvider grounding={grounding}>
        <div className="space-y-4">
          <Banner chart={chart} />
          <Alerts chart={chart} />
          <Wounds chart={chart} />
          <Tabs defaultValue="overview">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <TabsList>
                {TABS.map((t) => (
                  <TabsTrigger key={t.value} value={t.value}>
                    {t.label}
                  </TabsTrigger>
                ))}
              </TabsList>
              <GroundingSummary grounding={grounding} />
            </div>
            {TABS.map(({ value, render: Render }) => (
              <TabsContent key={value} value={value}>
                <Render chart={chart} />
              </TabsContent>
            ))}
          </Tabs>
        </div>
      </GroundingProvider>
    </TooltipProvider>
  )
}
