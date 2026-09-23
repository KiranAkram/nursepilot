import { useEffect, useRef } from "react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

/** The three intake-gate outcomes that get the retro "item get" treatment. */
export type SplashKind = "accepted" | "rejected" | "paused"

const COPY: Record<SplashKind, { tag: string; title: string; body: string }> = {
  accepted: {
    tag: "+1 chart",
    title: "Packet get!",
    body: "Discharge packet confirmed. Extracting now — grab a coffee, this takes a minute.",
  },
  rejected: {
    tag: "item refused",
    title: "Not an SNF packet",
    body: "This one doesn't fit in the medkit. Got a hospital discharge packet? Slide it over.",
  },
  paused: {
    tag: "intake offline",
    title: "Paused",
    body: "The intake desk stepped away. Give it a minute, then press retry.",
  },
}

const ACCEPTED_MS = 4000

export function IntakeSplash({
  kind,
  onClose,
  onRetry,
}: {
  kind: SplashKind
  onClose: () => void
  /** Only meaningful for `paused`: re-submit the same file. */
  onRetry?: () => void
}) {
  const buttonRef = useRef<HTMLButtonElement>(null)
  // Keep the latest callback without re-arming the effect (and its timer) on every render.
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose

  useEffect(() => {
    buttonRef.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCloseRef.current()
    }
    window.addEventListener("keydown", onKey)
    const timer =
      kind === "accepted" ? window.setTimeout(() => onCloseRef.current(), ACCEPTED_MS) : undefined
    return () => {
      window.removeEventListener("keydown", onKey)
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [kind])

  const { tag, title, body } = COPY[kind]

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="intake-splash-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={kind === "accepted" ? onClose : undefined}
    >
      <div className={cn("pixel-card", `pixel-card--${kind}`)} onClick={(e) => e.stopPropagation()}>
        <div className="pixel-stage">
          {kind === "accepted" && <Medkit />}
          {kind === "rejected" && <MysteryBox />}
          {kind === "paused" && <PausedScreen />}
        </div>
        <p className="pixel-tag">{tag}</p>
        <h2 id="intake-splash-title" className="pixel-title">
          {title}
        </h2>
        <p className="pixel-body">{body}</p>

        <div className="mt-5 flex justify-center gap-2">
          {kind === "rejected" && (
            <Button ref={buttonRef} onClick={onClose}>
              Try another
            </Button>
          )}
          {kind === "paused" && (
            <>
              <Button ref={buttonRef} onClick={onRetry ?? onClose}>
                Retry upload
              </Button>
              <Button variant="ghost" onClick={onClose} className="text-inherit hover:bg-white/10">
                Back
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// --- Pixel art -------------------------------------------------------------
// Hand-placed rects on a small grid + shape-rendering="crispEdges" gives the
// 8-bit look without image assets. Animation lives in index.css (.pixel-*).

const INK = "#161a2b"

function Medkit() {
  return (
    <>
      <svg viewBox="0 0 16 12" className="pixel-art pixel-art--medkit" aria-hidden="true">
        <rect x="5" y="0" width="6" height="2" fill={INK} />
        <rect x="6" y="1" width="4" height="1" fill="#f6f7fb" />
        <rect x="1" y="2" width="14" height="10" fill={INK} />
        <rect x="2" y="3" width="12" height="8" fill="#f6f7fb" />
        <rect x="7" y="4" width="2" height="6" fill="#e5322d" />
        <rect x="5" y="6" width="6" height="2" fill="#e5322d" />
      </svg>
      <span className="pixel-sparkle" style={{ top: 6, left: "22%" }} />
      <span className="pixel-sparkle" style={{ top: 18, right: "20%", animationDelay: ".3s" }} />
      <span className="pixel-sparkle" style={{ bottom: 10, left: "30%", animationDelay: ".6s" }} />
    </>
  )
}

function MysteryBox() {
  // "?" glyph on a 5x7 grid, offset into a 12x12 box.
  const q: Array<[number, number, number]> = [
    [4, 2, 3],
    [3, 3, 1],
    [7, 3, 1],
    [7, 4, 1],
    [6, 5, 1],
    [5, 6, 1],
    [5, 8, 1],
  ]
  return (
    <svg viewBox="0 0 12 12" className="pixel-art pixel-art--mystery" aria-hidden="true">
      <rect x="0" y="0" width="12" height="12" fill={INK} />
      <rect x="1" y="1" width="10" height="10" fill="#9aa1b5" />
      {q.map(([x, y, w]) => (
        <rect key={`${x}-${y}`} x={x} y={y} width={w} height="1" fill={INK} />
      ))}
    </svg>
  )
}

function PausedScreen() {
  return (
    <svg viewBox="0 0 16 10" className="pixel-art" aria-hidden="true">
      <rect x="0" y="0" width="16" height="10" fill="#1c2340" />
      <rect x="5" y="2" width="2" height="6" fill="#e6f0ff" />
      <rect x="9" y="2" width="2" height="6" fill="#e6f0ff" />
      <rect x="1" y="8" width="1" height="1" fill="#e6f0ff" className="pixel-cursor" />
    </svg>
  )
}
