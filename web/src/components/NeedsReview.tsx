import { AlertTriangle } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { FlaggedField } from "@/types/chart"

function renderValue(value: unknown): string {
  if (value === null || value === undefined) return "—"
  if (typeof value === "object") return JSON.stringify(value)
  return String(value)
}

/**
 * Values Gemini extracted that failed schema validation. Rather than failing the
 * whole chart, the worker quarantines them here for a nurse to review against the
 * source. Read-only for now — accept/correct needs persistence (no DB yet).
 */
export function NeedsReview({ flagged }: { flagged: FlaggedField[] }) {
  if (flagged.length === 0) return null
  return (
    <Card className="border-amber-300 bg-amber-50/50">
      <CardHeader className="flex-row items-center gap-2 space-y-0">
        <AlertTriangle className="size-4 text-amber-600" />
        <CardTitle className="text-amber-800">Needs review</CardTitle>
        <Badge variant="warning">{flagged.length}</Badge>
      </CardHeader>
      <CardContent>
        <p className="mb-3 text-sm text-muted-foreground">
          These values couldn't be validated and were left out of the chart. Check them against
          the source document.
        </p>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="border-b px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Field
              </th>
              <th className="border-b px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Extracted value
              </th>
              <th className="border-b px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Why
              </th>
            </tr>
          </thead>
          <tbody>
            {flagged.map((f, i) => (
              <tr key={i}>
                <td className="border-b px-3 py-2 align-top">
                  <span className="font-mono text-xs">{f.path}</span>
                </td>
                <td className="border-b px-3 py-2 align-top text-sm font-medium">
                  {renderValue(f.value)}
                </td>
                <td className="border-b px-3 py-2 align-top text-sm text-muted-foreground">
                  {f.reason}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  )
}
