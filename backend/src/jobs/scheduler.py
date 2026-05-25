import logging

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.jobs.jobs import (
    job_12wochen_warnung,
    job_belegungsbericht,
    job_cleanup,
    job_ueberkapazitaet,
)

logger = logging.getLogger(__name__)

JOB_REGISTRY = [
    {"func": job_12wochen_warnung, "trigger": "cron", "hour": 6, "minute": 0},
    {"func": job_ueberkapazitaet, "trigger": "cron", "hour": 6, "minute": 10},
    {"func": job_belegungsbericht, "trigger": "cron", "day_of_week": "mon", "hour": 7},
    {"func": job_cleanup, "trigger": "cron", "hour": 3},
]


def _on_job_error(event) -> None:
    logger.error(
        "Scheduled job '%s' raised an exception: %s",
        event.job_id,
        event.exception,
        exc_info=event.traceback,
    )


def _on_job_missed(event) -> None:
    logger.warning("Scheduled job '%s' missed its fire time", event.job_id)


def create_and_start() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_listener(_on_job_error, EVENT_JOB_ERROR)
    scheduler.add_listener(_on_job_missed, EVENT_JOB_MISSED)
    for entry in JOB_REGISTRY:
        entry = dict(entry)
        func = entry.pop("func")
        trigger = entry.pop("trigger")
        scheduler.add_job(func, trigger, **entry)
    scheduler.start()
    return scheduler


def stop(scheduler: AsyncIOScheduler) -> None:
    scheduler.shutdown(wait=False)
