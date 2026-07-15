import os
import re
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from agent.storage.database import get_setting

_DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_DAY_VI = {
    "mon": "Thứ 2", "tue": "Thứ 3", "wed": "Thứ 4", "thu": "Thứ 5",
    "fri": "Thứ 6", "sat": "Thứ 7", "sun": "Chủ nhật",
}
_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
_SYNTAX_HINT = "Cú pháp: !schedule mon,fri 08:30 (ngày: mon-sun hoặc 0-6, giờ: HH:MM)"


def parse_schedule(days_arg: str, time_arg: str) -> tuple[str, str]:
    """Validate + chuẩn hóa lịch. Trả (days, 'HH:MM'). Sai định dạng -> ValueError."""
    normalized: list[str] = []
    for token in days_arg.split(","):
        tok = token.strip().lower()
        if not tok:
            raise ValueError(_SYNTAX_HINT)
        if tok.isdigit():
            idx = int(tok)
            if not 0 <= idx <= 6:
                raise ValueError(_SYNTAX_HINT)
            name = _DAY_NAMES[idx]
        elif tok in _DAY_NAMES:
            name = tok
        else:
            raise ValueError(_SYNTAX_HINT)
        if name not in normalized:
            normalized.append(name)
    if not normalized:
        raise ValueError(_SYNTAX_HINT)

    m = _TIME_RE.match(time_arg.strip())
    if not m:
        raise ValueError(_SYNTAX_HINT)
    time_str = f"{int(m.group(1)):02d}:{m.group(2)}"
    return ",".join(normalized), time_str


def format_days_vi(days: str) -> str:
    """'mon,fri' -> 'Thứ 2, Thứ 6'."""
    return ", ".join(_DAY_VI[d.strip().lower()] for d in days.split(","))


_scheduler: BackgroundScheduler | None = None


def _load_schedule() -> tuple[str, str]:
    """Lịch theo thứ tự ưu tiên: DB -> .env -> mặc định code."""
    days = get_setting("schedule_days") or os.getenv("REPORT_SCHEDULE_DAY", "mon")
    time_str = get_setting("schedule_time") or os.getenv("REPORT_SCHEDULE_TIME", "08:00")
    return days, time_str


def init_scheduler(crawl_and_report_fn) -> BackgroundScheduler:
    global _scheduler
    days, time_str = _load_schedule()
    timezone = os.getenv("REPORT_TIMEZONE", "Asia/Ho_Chi_Minh")
    hour, minute = time_str.split(":")

    _scheduler = BackgroundScheduler(timezone=timezone)
    _scheduler.add_job(
        crawl_and_report_fn,
        CronTrigger(
            day_of_week=days,
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


def reschedule(days: str, time_str: str) -> str:
    """Đổi trigger job weekly_report đang chạy. Trả chuỗi lần chạy kế tiếp."""
    if not _scheduler:
        raise RuntimeError("Scheduler chưa khởi động")
    hour, minute = time_str.split(":")
    _scheduler.reschedule_job(
        "weekly_report",
        trigger=CronTrigger(
            day_of_week=days,
            hour=int(hour),
            minute=int(minute),
            timezone=_scheduler.timezone,
        ),
    )
    return get_next_run()


def stop() -> None:
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
