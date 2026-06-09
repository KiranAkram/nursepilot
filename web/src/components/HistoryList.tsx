import { FileText, Loader2, Plus, RefreshCw } from "lucide-react"
import { useEffect, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { listCharts } from "@/lib/api"
import type { JobSummary } from "@/types/chart"

const STATUS_TONE = {
  done: "success",
  processing: "secondary",
  error: "destructive",
} as const

function fmt(ts: string | null): string {
  if (!ts) return "—"
  const d = new Date(ts)
  return Number.isNaN(d.getTime()) ? ts : d.toLocaleString()
}

export function HistoryList({
  onOpen,
  onNew,
}: {
  onOpen: (jobId: string) => void
  onNew: () => void
}) {
  const [rows, setRows] = useState<JobSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setError(null)
    try {
      setRows(await listCharts())
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load")
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <Card>
      <CardContent className="p-4">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            Extractions
          </h2>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={load}>
              <RefreshCw /> Refresh
            </Button>
            <Button size="sm" onClick={onNew}>
              <Plus /> New upload
            </Button>
          </div>
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}
        {rows === null && !error && (
          <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" /> Loading…
          </div>
        )}
        {rows?.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-10 text-center text-muted-foreground">
            <FileText className="size-8" />
            <p className="text-sm">No extractions yet. Upload a discharge packet to start.</p>
          </div>
        )}

        {rows && rows.length > 0 && (
          <table className="w-full border-collapse">
            <thead>
              <tr>
                {["Patient", "MRN", "File", "Status", "Updated"].map((h) => (
                  <th
                    key={h}
                    className="border-b px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.job_id}
                  onClick={() => r.status === "done" && onOpen(r.job_id)}
                  className={
                    "border-b text-sm " +
                    (r.status === "done"
                      ? "cursor-pointer hover:bg-muted/50"
                      : "text-muted-foreground")
                  }
                >
                  <td className="px-3 py-2 font-medium">{r.patient_name ?? "—"}</td>
                  <td className="px-3 py-2">{r.mrn ?? "—"}</td>
                  <td className="px-3 py-2">{r.filename ?? "—"}</td>
                  <td className="px-3 py-2">
                    <Badge variant={STATUS_TONE[r.status]}>{r.status}</Badge>
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">{fmt(r.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  )
}
