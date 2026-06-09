import { Activity, ArrowLeft } from "lucide-react"
import { useState } from "react"

import { ChartView } from "@/components/ChartView"
import { HistoryList } from "@/components/HistoryList"
import { Uploader } from "@/components/Uploader"
import { Button } from "@/components/ui/button"
import { getJob, pollJob, updateChart, uploadPdf } from "@/lib/api"
import type { FlaggedField, GroundingResult, PatientChart } from "@/types/chart"

type Loaded = {
  jobId: string
  chart: PatientChart
  grounding: GroundingResult[]
  flagged: FlaggedField[]
  label: string
}

type View =
  | { kind: "list" }
  | { kind: "upload"; busy: boolean; error?: string }
  | { kind: "chart"; data: Loaded }

export default function App() {
  const [view, setView] = useState<View>({ kind: "list" })

  async function handleUpload(file: File) {
    setView({ kind: "upload", busy: true })
    try {
      const jobId = await uploadPdf(file)
      const job = await pollJob(jobId)
      if (job.status === "error") {
        setView({ kind: "upload", busy: false, error: job.detail })
        return
      }
      setView({
        kind: "chart",
        data: {
          jobId,
          chart: job.chart,
          grounding: job.grounding,
          flagged: job.flagged,
          label: file.name,
        },
      })
    } catch (e) {
      setView({ kind: "upload", busy: false, error: e instanceof Error ? e.message : "Error" })
    }
  }

  async function handleOpen(jobId: string) {
    const job = await getJob(jobId)
    if (job.status !== "done") return
    setView({
      kind: "chart",
      data: {
        jobId,
        chart: job.chart,
        grounding: job.grounding,
        flagged: job.flagged,
        label: job.chart.demographics
          ? `${job.chart.demographics.family_name}, ${job.chart.demographics.given_name}`
          : jobId,
      },
    })
  }

  async function handleSave(jobId: string, chart: PatientChart) {
    const updated = await updateChart(jobId, chart)
    setView((v) =>
      v.kind === "chart" ? { kind: "chart", data: { ...v.data, chart: updated.chart } } : v,
    )
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <header className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="size-6 text-primary" />
          <h1 className="text-lg font-semibold">NursePilot</h1>
          {view.kind === "chart" && (
            <span className="text-sm text-muted-foreground">· {view.data.label}</span>
          )}
        </div>
        {view.kind !== "list" && (
          <Button variant="ghost" size="sm" onClick={() => setView({ kind: "list" })}>
            <ArrowLeft /> All extractions
          </Button>
        )}
      </header>

      {view.kind === "list" && (
        <HistoryList onOpen={handleOpen} onNew={() => setView({ kind: "upload", busy: false })} />
      )}

      {view.kind === "upload" && (
        <div className="space-y-4">
          <Uploader onSelect={handleUpload} busy={view.busy} />
          {view.error && (
            <p className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              {view.error}
            </p>
          )}
        </div>
      )}

      {view.kind === "chart" && (
        <ChartView
          chart={view.data.chart}
          grounding={view.data.grounding}
          flagged={view.data.flagged}
          onSave={(chart) => handleSave(view.data.jobId, chart)}
        />
      )}
    </div>
  )
}
