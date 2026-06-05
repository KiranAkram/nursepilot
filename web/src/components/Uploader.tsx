import { FileText, Loader2, Upload } from "lucide-react"
import { useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

export function Uploader({
  onSelect,
  busy,
}: {
  onSelect: (file: File) => void
  busy: boolean
}) {
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
              {busy ? "Extracting chart…" : "Drop a discharge packet PDF"}
            </p>
            <p className="text-sm text-muted-foreground">
              {busy ? "This can take up to a minute." : "or choose a file to upload"}
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
