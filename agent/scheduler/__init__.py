import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

_scheduler: BackgroundScheduler | None = None


def init_scheduler(crawl_and_report_fn) -> BackgroundScheduler:
    global _scheduler
    day = os.getenv("REPORT_SCHEDULE_DAY", "mon")
    day_of_week = int(day) if day.isdigit() else day
    time_str = os.getenv("REPORT_SCHEDULE_TIME", "08:00")
    timezone = os.getenv("REPORT_TIMEZONE", "Asia/Ho_Chi_Minh")
    hour, minute = time_str.split(":")

    _scheduler = BackgroundScheduler(timezone=timezone)
    _scheduler.add_job(
        crawl_and_report_fn,
        CronTrigger(
            day_of_week=day_of_week,
            hour=int(hour),
            minute=int(minute),
            timezone=timezone,
        ),
        id="weekly_report",
        name="Weekly Core Network Report",
        replace_existing=True,
    )
    _scheduler.start()
    return _scheduler


def get_next_run() -> str:
    if not _scheduler:
        return "Scheduler not started"
    job = _scheduler.get_job("weekly_report")
    if job and job.next_run_time:
        return job.next_run_time.strftime("%Y-%m-%d %H:%M %Z")
    return "Unknown"


def stop() -> None:
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
