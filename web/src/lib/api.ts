import type { JobStatus } from "@/types/chart"

const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000"

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
