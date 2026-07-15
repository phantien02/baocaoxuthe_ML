import pytest
from agent.scheduler import parse_schedule, format_days_vi
from agent.scheduler import init_scheduler, reschedule, get_next_run, stop
from agent.storage.database import init_db, set_setting


@pytest.fixture
def stop_scheduler_after():
    yield
    stop()


def _noop():
    pass


def test_parse_single_day():
    assert parse_schedule("mon", "08:00") == ("mon", "08:00")


def test_parse_multi_day():
    assert parse_schedule("mon,fri", "08:30") == ("mon,fri", "08:30")


def test_parse_case_insensitive():
    assert parse_schedule("MON,Fri", "08:30") == ("mon,fri", "08:30")


def test_parse_numeric_days_normalized_to_names():
    # 0=mon ... 6=sun
    assert parse_schedule("0,4", "08:00") == ("mon,fri", "08:00")


def test_parse_dedupes_keeping_order():
    assert parse_schedule("fri,mon,fri", "08:00") == ("fri,mon", "08:00")


def test_parse_bad_day_raises():
    with pytest.raises(ValueError):
        parse_schedule("funday", "08:00")


def test_parse_out_of_range_number_raises():
    with pytest.raises(ValueError):
        parse_schedule("7", "08:00")


def test_parse_bad_time_raises():
    with pytest.raises(ValueError):
        parse_schedule("mon", "25:00")
    with pytest.raises(ValueError):
        parse_schedule("mon", "8h30")
    with pytest.raises(ValueError):
        parse_schedule("mon", "08:60")


def test_format_days_vi_maps_all():
    assert format_days_vi("mon,tue,wed,thu,fri,sat,sun") == (
        "Thứ 2, Thứ 3, Thứ 4, Thứ 5, Thứ 6, Thứ 7, Chủ nhật"
    )


def test_init_scheduler_prefers_db_over_env(monkeypatch, stop_scheduler_after):
    init_db()
    monkeypatch.setenv("REPORT_SCHEDULE_DAY", "mon")
    monkeypatch.setenv("REPORT_SCHEDULE_TIME", "08:00")
    set_setting("schedule_days", "fri")
    set_setting("schedule_time", "09:30")
    sched = init_scheduler(_noop)
    trigger = str(sched.get_job("weekly_report").trigger)
    assert "fri" in trigger
    assert "hour='9'" in trigger
    assert "minute='30'" in trigger


def test_init_scheduler_falls_back_to_env(monkeypatch, stop_scheduler_after):
    init_db()  # DB rỗng, không set schedule_*
    monkeypatch.setenv("REPORT_SCHEDULE_DAY", "wed")
    monkeypatch.setenv("REPORT_SCHEDULE_TIME", "07:15")
    sched = init_scheduler(_noop)
    trigger = str(sched.get_job("weekly_report").trigger)
    assert "wed" in trigger
    assert "hour='7'" in trigger
    assert "minute='15'" in trigger


def test_reschedule_updates_job(stop_scheduler_after):
    init_db()
    init_scheduler(_noop)
    result = reschedule("sat", "10:45")
    trigger = str(get_next_run.__globals__["_scheduler"].get_job("weekly_report").trigger)
    assert "sat" in trigger
    assert "hour='10'" in trigger
    assert "minute='45'" in trigger
    assert result and result != "Unknown"
