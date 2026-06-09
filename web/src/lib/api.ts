import type { JobStatus, JobSummary, PatientChart } from "@/types/chart"

// Prefer the runtime-injected config (set by the container at startup), so one
// built image serves every environment. Falls back to the build-time VITE_API_URL
// for local `npm run dev`, where the placeholder is left untouched.
function resolveApiUrl(): string {
  const injected = window.__APP_CONFIG__?.apiUrl
  if (injected && injected !== "__API_URL__") return injected
  return (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000"
}

const API_URL = resolveApiUrl()

export async function uploadPdf(file: File): Promise<string> {
  const body = new FormData()
  body.append("file", file)
  const res = await fetch(`${API_URL}/charts`, { method: "POST", body })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail.detail ?? `Upload failed (${res.status})`)
  }
  const data = (await res.json()) as { job_id: string }
  return data.job_id
}

export async function getJob(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_URL}/charts/${jobId}`)
  if (!res.ok) throw new Error(`Poll failed (${res.status})`)
  return (await res.json()) as JobStatus
}

export async function listCharts(): Promise<JobSummary[]> {
  const res = await fetch(`${API_URL}/charts`)
  if (!res.ok) throw new Error(`List failed (${res.status})`)
  return (await res.json()) as JobSummary[]
}

export async function updateChart(
  jobId: string,
  chart: PatientChart,
): Promise<Extract<JobStatus, { status: "done" }>> {
  const res = await fetch(`${API_URL}/charts/${jobId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(chart),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(
      typeof detail.detail === "string" ? detail.detail : `Save failed (${res.status})`,
    )
  }
  return (await res.json()) as Extract<JobStatus, { status: "done" }>
}

/** Poll until the job is done or errors. Resolves with the terminal status. */
export async function pollJob(
  jobId: string,
  { intervalMs = 1500, signal }: { intervalMs?: number; signal?: AbortSignal } = {},
): Promise<Extract<JobStatus, { status: "done" | "error" }>> {
  for (;;) {
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError")
    const job = await getJob(jobId)
    if (job.status !== "processing") return job
    await new Promise((r) => setTimeout(r, intervalMs))
  }
}
