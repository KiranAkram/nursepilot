"""Event-driven job runner: LISTEN on Postgres, claim pending extractions, run them.

Postgres is both the queue (the `extractions` table) and the event bus (NOTIFY).
The listener blocks on the socket doing nothing until the API fires a NOTIFY,
then drains every pending row. The notification is only a hint: each pass also
sweeps the table, so a missed NOTIFY or a worker that died mid-job costs at most
SWEEP_SECONDS of latency, never a lost job.

Runs as a daemon thread inside the API process (api/main.py). Several instances
are safe: claims use FOR UPDATE SKIP LOCKED.
"""

import logging
import os
import time

import psycopg
from psycopg import sql

from db.notify import CHANNEL
from db.session import psycopg_dsn
from jobqueue import claim, fail, reclaim_stale, reject
from jobs import extract_chart
from screening import NotAnSnfPacketError, ScreeningUnavailableError

log = logging.getLogger(__name__)

SWEEP_SECONDS = float(os.environ.get("WORKER_SWEEP_SECONDS", "30"))
RECONNECT_SECONDS = 5.0


def run_forever() -> None:
    """Serve jobs until the process exits, reconnecting if the DB drops."""
    while True:
        try:
            _serve()
        except psycopg.OperationalError as exc:
            log.warning(
                "worker: db connection lost (%s); retrying in %ss",
                exc,
                RECONNECT_SECONDS,
            )
            time.sleep(RECONNECT_SECONDS)


def _serve() -> None:
    with psycopg.connect(psycopg_dsn(), autocommit=True) as conn:
        conn.execute(sql.SQL("LISTEN {}").format(sql.Identifier(CHANNEL)))
        log.info("worker: listening on %s", CHANNEL)
        while True:
            reclaimed = reclaim_stale(conn)
            if reclaimed:
                log.warning("worker: requeued %d stale job(s)", reclaimed)
            drain(conn)
            # Block until a NOTIFY arrives or the sweep interval elapses.
            for _ in conn.notifies(timeout=SWEEP_SECONDS, stop_after=1):
                pass


def drain(conn: psycopg.Connection) -> int:
    """Run every claimable job; returns how many were attempted."""
    attempted = 0
    while (job := claim(conn)) is not None:
        job_id, pdf = job
        attempted += 1
        if pdf is None:
            # Nothing to extract from (e.g. a row left over from the pre-queue
            # deploy). Retrying can't help.
            fail(conn, job_id, "no PDF stored for this job", retryable=False)
            continue
        try:
            extract_chart(job_id, pdf)
            log.info("worker: job %s done", job_id)
        except NotAnSnfPacketError as exc:
            log.info("worker: job %s rejected by screening", job_id)
            reject(conn, job_id, exc.screening)
        except ScreeningUnavailableError as exc:
            # Strict gate: never extract unscreened. Retried like any failure;
            # the verdict records that the gate itself was down.
            log.warning("worker: job %s screening unavailable: %s", job_id, exc)
            fail(
                conn,
                job_id,
                str(exc),
                screening={"outcome": "unavailable", "reason": str(exc)},
            )
        except Exception as exc:
            log.exception("worker: job %s failed", job_id)
            fail(conn, job_id, str(exc))
    return attempted
