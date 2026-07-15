import pytest
from agent.scheduler import parse_schedule, format_days_vi


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
