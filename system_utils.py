"""System utilities for dashboard health checks and monitoring."""
from typing import Dict, Optional, List


def check_redis_health(redis_url: str = 'redis://localhost:6379/0') -> Dict[str, bool | str]:
    """Check Redis connection health. Returns dict with 'connected' and 'error' (if any)."""
    try:
        from redis import Redis
        redis_conn = Redis.from_url(redis_url)
        redis_conn.ping()
        return {'connected': True, 'url': redis_url}
    except Exception as e:
        return {'connected': False, 'error': str(e), 'url': redis_url}


def get_job_status(job_id: str, redis_url: str = 'redis://localhost:6379/0') -> Optional[str]:
    """Fetch job status from Redis/RQ. Returns 'queued', 'started', 'finished', 'failed', or None."""
    try:
        from redis import Redis
        from rq.job import Job
        redis_conn = Redis.from_url(redis_url)
        job = Job.fetch(job_id, connection=redis_conn)
        return job.get_status()
    except Exception:
        return None


def get_queue_stats(redis_url: str = 'redis://localhost:6379/0') -> Dict:
    """Get queue depth and job counts. Returns dict with counts."""
    try:
        from redis import Redis
        from rq import Queue
        redis_conn = Redis.from_url(redis_url)
        q = Queue('advisor', connection=redis_conn)
        return {
            'queue_depth': len(q),
            'jobs_started': len(q.started_job_registry),
            'jobs_finished': len(q.finished_job_registry),
            'jobs_failed': len(q.failed_job_registry),
        }
    except Exception as e:
        return {'error': str(e)}


def bulk_enqueue_advice(
    alert_ids: List[int],
    db_path: str,
    redis_url: str,
    remediation_backend: str | None = None,
) -> int:
    """Enqueue multiple alerts for advice generation. Returns count enqueued."""
    try:
        from redis import Redis
        from rq import Queue
        from db import get_session, Alert, AuditLog
        
        redis_conn = Redis.from_url(redis_url)
        q = Queue('advisor', connection=redis_conn)
        session = get_session(db_path)
        
        enqueued = 0
        for alert_id in alert_ids:
            alert = session.query(Alert).filter(Alert.id == alert_id).one_or_none()
            if alert and not alert.advice:
                job = q.enqueue(
                    "tasks.generate_advice_for_alert",
                    alert_id,
                    db_path,
                    remediation_backend,
                )
                alert.advice_job_id = job.id
                alert.advice_status = 'queued'
                session.add(AuditLog(alert_id=alert_id, action='bulk_enqueue', actor='dashboard'))
                enqueued += 1
        session.commit()
        session.close()
        return enqueued
    except Exception as e:
        raise RuntimeError(f"Bulk enqueue failed: {e}")


def get_redis_connection_command() -> str:
    """Return the command to start Redis."""
    return "redis-server"


def get_worker_start_command() -> str:
    """Return the command to start an RQ worker."""
    return "rq worker advisor"
