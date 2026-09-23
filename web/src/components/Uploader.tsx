import { FileText, Loader2, Upload } from "lucide-react"
import { useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { JobPhase } from "@/types/chart"

export function Uploader({
  onSelect,
  busy,
  phase,
}: {
  onSelect: (file: File) => void
  busy: boolean
  /** Current pipeline phase while busy; drives the status text. */
  phase?: JobPhase
}) {
  const extracting = phase === "extracting"
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  function handleFiles(files: FileList | null) {
    const file = files?.[0]
    if (file) onSelect(file)
  }

  return (
    <Card>
      <CardContent className="p-6">
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragging(false)
            if (!busy) handleFiles(e.dataTransfer.files)
          }}
          className={cn(
            "flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 text-center transition-colors",
            dragging ? "border-primary bg-primary/5" : "border-border",
            busy && "opacity-60",
          )}
        >
          {busy ? (
            <Loader2 className="size-8 animate-spin text-primary" />
          ) : (
            <FileText className="size-8 text-muted-foreground" />
          )}
          <div>
            <p className="font-medium">
              {!busy
                ? "Drop a discharge packet PDF"
                : extracting
                  ? "Extracting chart…"
                  : "Checking the packet…"}
            </p>
            <p className="text-sm text-muted-foreground">
              {!busy
                ? "or choose a file to upload"
                : extracting
                  ? "This can take up to a minute."
                  : "Making sure this is a discharge packet."}
            </p>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf,.pdf"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
          <Button onClick={() => inputRef.current?.click()} disabled={busy} variant="outline">
            <Upload /> Choose PDF
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
