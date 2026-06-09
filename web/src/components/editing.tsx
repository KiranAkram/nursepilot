import { createContext, useContext } from "react"

type EditCtx = {
  editing: boolean
  set: (path: string, value: unknown) => void
}

const Ctx = createContext<EditCtx>({ editing: false, set: () => {} })

export const EditProvider = Ctx.Provider
export const useEdit = () => useContext(Ctx)

/** Immutable nested set by dot-path, e.g. "demographics.family_name". */
export function setPath<T>(obj: T, path: string, value: unknown): T {
  const keys = path.split(".")
  const clone = structuredClone(obj)
  let cur: Record<string, unknown> = clone as Record<string, unknown>
  for (let i = 0; i < keys.length - 1; i++) {
    cur[keys[i]] = cur[keys[i]] ?? {}
    cur = cur[keys[i]] as Record<string, unknown>
  }
  cur[keys[keys.length - 1]] = value
  return clone
}
