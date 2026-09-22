"""Postgres-as-queue primitives over the `extractions` table.

The table *is* the queue: `status='pending'` rows are work. NOTIFY (see
db.notify) is only a wake-up hint, so every function here must also be correct
when called on a timer with no notification at all.

All statements use plain psycopg on an autocommit connection: each is a single
atomic UPDATE, which is what makes claiming safe across concurrent workers.
"""

import psycopg

MAX_ATTEMPTS = 3
STALE_AFTER = "20 minutes"  # > any plausible single extraction incl. Gemini retries

_CLAIM = """
UPDATE extractions
SET status = 'processing', updated_at = now()
WHERE id = (
    SELECT id FROM extractions
    WHERE status = 'pending'
    ORDER BY created_at
    LIMIT 1
    FOR UPDATE SKIP LOCKED
)
RETURNING id, pdf
"""

# `retry_count` on the right-hand side is the pre-update value throughout, so
# every CASE sees the same attempt number.
_FAIL = """
UPDATE extractions
SET retry_count = retry_count + 1,
    status = CASE WHEN %(retry)s AND retry_count + 1 < %(max)s
                  THEN 'pending' ELSE 'error' END,
    pdf    = CASE WHEN %(retry)s AND retry_count + 1 < %(max)s
                  THEN pdf ELSE NULL END,
    error = %(error)s,
    updated_at = now()
WHERE id = %(id)s
"""

_RECLAIM_STALE = """
UPDATE extractions
SET retry_count = retry_count + 1,
    status = CASE WHEN retry_count + 1 < %(max)s THEN 'pending' ELSE 'error' END,
    pdf    = CASE WHEN retry_count + 1 < %(max)s THEN pdf ELSE NULL END,
    error  = CASE WHEN retry_count + 1 < %(max)s THEN error
                  ELSE 'worker died mid-job; retries exhausted' END,
    updated_at = now()
WHERE status = 'processing' AND updated_at < now() - %(stale)s::interval
"""


def claim(conn: psycopg.Connection) -> tuple[str, bytes | None] | None:
    """Atomically take the oldest pending job. Returns (job_id, pdf) or None."""
    row = conn.execute(_CLAIM).fetchone()
    if row is None:
        return None
    job_id, pdf = row
    return job_id, (bytes(pdf) if pdf is not None else None)


def fail(
    conn: psycopg.Connection, job_id: str, error: str, *, retryable: bool = True
) -> None:
    """Record a failed attempt: back to `pending` if attempts remain, else `error`.

    The final failure drops the PDF bytes; nothing will read them again.
    """
    conn.execute(
        _FAIL, {"id": job_id, "error": error, "retry": retryable, "max": MAX_ATTEMPTS}
    )


def reclaim_stale(conn: psycopg.Connection) -> int:
    """Requeue jobs whose worker died mid-run (still `processing` after STALE_AFTER).

    Counts as a failed attempt so a job that crashes the worker every time can't
    loop forever. Returns the number of rows touched.
    """
    cur = conn.execute(_RECLAIM_STALE, {"max": MAX_ATTEMPTS, "stale": STALE_AFTER})
    return cur.rowcount
