import { Activity, RotateCcw } from "lucide-react"
import { useState } from "react"

import { ChartView } from "@/components/ChartView"
import { Uploader } from "@/components/Uploader"
import { Button } from "@/components/ui/button"
import { pollJob, uploadPdf } from "@/lib/api"
import type { GroundingResult, PatientChart } from "@/types/chart"

type State =
  | { kind: "idle" }
  | { kind: "working" }
  | { kind: "done"; chart: PatientChart; grounding: GroundingResult[]; file: string }
  | { kind: "error"; message: string }

export default function App() {
  const [state, setState] = useState<State>({ kind: "idle" })

  async function handleSelect(file: File) {
    setState({ kind: "working" })
    try {
      const jobId = await uploadPdf(file)
      const job = await pollJob(jobId)
      if (job.status === "error") {
        setState({ kind: "error", message: job.detail })
        return
      }
      setState({ kind: "done", chart: job.chart, grounding: job.grounding, file: file.name })
    } catch (e) {
      setState({ kind: "error", message: e instanceof Error ? e.message : "Unexpected error" })
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-6">
      <header className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="size-6 text-primary" />
          <h1 className="text-lg font-semibold">NursePilot</h1>
          {state.kind === "done" && (
            <span className="text-sm text-muted-foreground">· {state.file}</span>
          )}
        </div>
        {state.kind !== "idle" && (
          <Button variant="ghost" size="sm" onClick={() => setState({ kind: "idle" })}>
            <RotateCcw /> New upload
          </Button>
        )}
      </header>

      {state.kind === "done" ? (
        <ChartView chart={state.chart} grounding={state.grounding} />
      ) : (
        <div className="space-y-4">
          <Uploader onSelect={handleSelect} busy={state.kind === "working"} />
          {state.kind === "error" && (
            <p className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              {state.message}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
