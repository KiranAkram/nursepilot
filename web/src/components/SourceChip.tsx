import { CheckCircle2, FileText, TriangleAlert } from "lucide-react"

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useGrounding } from "@/components/grounding"
import { cn } from "@/lib/utils"
import type { SourceRef } from "@/types/chart"

/**
 * Traceability chip for a single extracted fact: page #, model confidence, and
 * the verbatim quote (on hover). Color reflects the grounding check — whether
 * that quote was actually found on the cited PDF page.
 *
 * `path` is the SourceRef's own dotted path (e.g. "diagnoses[0].source"), used
 * to look up the grounding verdict.
 */
export function SourceChip({ source, path }: { source: SourceRef; path: string }) {
  const grounding = useGrounding(path)
  const grounded = grounding?.grounded ?? null

  const tone =
    grounded === null
      ? "border-border bg-muted text-muted-foreground"
      : grounded
        ? "border-emerald-200 bg-emerald-50 text-emerald-700"
        : "border-amber-200 bg-amber-50 text-amber-700"

  const Icon = grounded === null ? FileText : grounded ? CheckCircle2 : TriangleAlert

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn(
            "inline-flex cursor-help items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-medium leading-none",
            tone,
          )}
        >
          <Icon className="!size-3" />p{source.page} · {Math.round(source.confidence * 100)}%
        </span>
      </TooltipTrigger>
      <TooltipContent>
        <div className="space-y-1">
          <div className="font-semibold">
            {grounded === null
              ? "Source (not verified)"
              : grounded
                ? "Grounded — quote found on cited page"
                : "Ungrounded — quote not found on cited page"}
          </div>
          <div className="text-muted-foreground">Page {source.page}</div>
          <blockquote className="border-l-2 border-border pl-2 italic">
            “{source.quote}”
          </blockquote>
        </div>
      </TooltipContent>
    </Tooltip>
  )
}
