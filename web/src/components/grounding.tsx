import { createContext, useContext } from "react"

import type { GroundingResult } from "@/types/chart"

// Map keyed by the SourceRef's dotted path (e.g. "diagnoses[0].source").
const GroundingContext = createContext<Map<string, GroundingResult>>(new Map())

export function GroundingProvider({
  grounding,
  children,
}: {
  grounding: GroundingResult[]
  children: React.ReactNode
}) {
  const map = new Map(grounding.map((g) => [g.field, g]))
  return <GroundingContext.Provider value={map}>{children}</GroundingContext.Provider>
}

export function useGrounding(path: string): GroundingResult | undefined {
  return useContext(GroundingContext).get(path)
}
