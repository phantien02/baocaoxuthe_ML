# Chỉnh lịch crawl/báo cáo runtime qua lệnh bot — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cho phép admin đổi lịch crawl/gửi báo cáo ngay lúc chạy qua lệnh `!schedule` trong Netchat, lưu bền vững vào DB, không cần restart.

**Architecture:** Lịch được lưu vào bảng key-value `settings` trong SQLite. `init_scheduler` đọc lịch theo thứ tự ưu tiên DB → `.env` → mặc định code. Lệnh bot `!schedule` (chỉ admin) validate tham số bằng hàm thuần `parse_schedule`, ghi DB rồi gọi `reschedule` để cập nhật job APScheduler đang chạy. Timezone vẫn cố định từ `.env`.

**Tech Stack:** Python 3.11, SQLite (`sqlite3`), APScheduler (`BackgroundScheduler` + `CronTrigger`), pytest + `unittest.mock`.

## Global Constraints

- `python -m pytest tests/ -q` phải xanh hết trước khi commit. Commit theo conventional commits.
- KHÔNG BAO GIỜ commit `.env` hoặc token/API key thật vào code, `.env.example`, tài liệu.
- Đổi schema DB: sửa `CREATE TABLE` **và** thêm `ALTER TABLE` migration trong `init_db()` nếu là thêm cột vào bảng cũ. Bảng `settings` là bảng **mới hoàn toàn** → chỉ cần `CREATE TABLE IF NOT EXISTS`, không cần ALTER.
- Không phá hành vi cũ: DB chưa có khóa lịch → phải fallback về `.env` đúng như hiện tại.
- Test dùng fixture sẵn có trong `tests/conftest.py` (`isolated_db` cấp `DB_PATH` tạm, `env_vars` cấp biến môi trường). Không cần tự set `DB_PATH`.
- APScheduler `day_of_week` nhận chuỗi tên ngày ngăn cách bằng phẩy (`"mon,fri"`) hoặc chuỗi số (`"0"`–`"6"`, 0=mon…6=sun). Truyền thẳng chuỗi `days` đã chuẩn hóa.

**Quyết định thiết kế (làm rõ so với spec):** `parse_schedule` chuẩn hóa **cả token số 0–6 về tên ngày** (`"0"` → `"mon"`, `"4"` → `"fri"`). Nhờ vậy giá trị lưu DB và truyền cho `format_days_vi` luôn đồng nhất là tên ngày, `format_days_vi` chỉ cần map tên → tiếng Việt.

---

## File Structure

- `agent/storage/database.py` (modify) — thêm bảng `settings` vào `init_db()` + 2 hàm `get_setting`/`set_setting`.
- `agent/scheduler/__init__.py` (modify) — thêm `parse_schedule`, `format_days_vi`, `reschedule`; sửa `init_scheduler` đọc DB→env; thêm hằng `_DAY_NAMES`, `_DAY_VI`.
- `agent/bot/commands.py` (modify) — thêm `is_admin`, nhánh lệnh `!schedule`/`!lịch`, thread `sender_name` xuống `_handle_command`, cập nhật `_help_text`.
- `agent/.env.example` (modify) — thêm `ADMIN_USERNAMES`.
- `tests/test_storage.py` (modify) — test `get_setting`/`set_setting`.
- `tests/test_scheduler.py` (create) — test `parse_schedule`, `format_days_vi`, `init_scheduler` ưu tiên DB, `reschedule`.
- `tests/test_commands.py` (modify) — test nhánh `!schedule` và `is_admin`.
- `TIEN_DO_DU_AN.md`, `HUONG_DAN_SU_DUNG_NEWBIE.md` (modify) — ghi tính năng mới.

---

## Task 1: Bảng `settings` + get_setting/set_setting

**Files:**
- Modify: `agent/storage/database.py` (thêm bảng trong `init_db()` ~dòng 20-48; thêm 2 hàm cuối file)
- Test: `tests/test_storage.py`

**Interfaces:**
- Produces:
  - `get_setting(key: str, default: str | None = None) -> str | None`
  - `set_setting(key: str, value: str) -> None`
  - Bảng `settings(key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TIMESTAMP)`

- [ ] **Step 1: Viết test thất bại**

Thêm vào cuối `tests/test_storage.py`:

```python
def test_settings_returns_default_when_missing():
    init_db()
    from agent.storage.database import get_setting
    assert get_setting("schedule_days") is None
    assert get_setting("schedule_days", "mon") == "mon"


def test_settings_set_then_get():
    init_db()
    from agent.storage.database import get_setting, set_setting
    set_setting("schedule_days", "mon,fri")
    assert get_setting("schedule_days") == "mon,fri"


def test_settings_upsert_overwrites():
    init_db()
    from agent.storage.database import get_setting, set_setting
    set_setting("schedule_time", "08:00")
    set_setting("schedule_time", "09:30")
    assert get_setting("schedule_time") == "09:30"


def test_init_db_creates_settings_table():
    init_db()
    import sqlite3, os
    conn = sqlite3.connect(os.environ["DB_PATH"])
    tables = {t[0] for t in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "settings" in tables
    conn.close()
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `python -m pytest tests/test_storage.py -q -k settings`
Expected: FAIL — `ImportError: cannot import name 'get_setting'`.

- [ ] **Step 3: Cài đặt tối thiểu**

Trong `agent/storage/database.py`, thêm bảng `settings` vào chuỗi `executescript` trong `init_db()` (ngay sau block `uploaded_docs`, trước dấu `"""` đóng):

```python
            CREATE TABLE IF NOT EXISTS settings (
                key        TEXT PRIMARY KEY,
                value      TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
```

Thêm 2 hàm vào cuối file:

```python
def get_setting(key: str, default: str | None = None) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET"
            " value = excluded.value, updated_at = CURRENT_TIMESTAMP",
            (key, value),
        )
```

- [ ] **Step 4: Chạy test để xác nhận pass**

Run: `python -m pytest tests/test_storage.py -q`
Expected: PASS toàn bộ.

- [ ] **Step 5: Commit**

```bash
git add agent/storage/database.py tests/test_storage.py
git commit -m "feat(storage): add settings key-value table with get/set helpers"
```

---

## Task 2: Hàm thuần parse_schedule + format_days_vi

**Files:**
- Modify: `agent/scheduler/__init__.py` (thêm hằng + 2 hàm thuần, trên cùng sau import)
- Test: `tests/test_scheduler.py` (create)

**Interfaces:**
- Produces:
  - `parse_schedule(days_arg: str, time_arg: str) -> tuple[str, str]` — trả về `(days_normalized, "HH:MM")`; `days_normalized` là tên ngày lowercase ngăn cách bằng phẩy, đã dedupe giữ thứ tự. Raise `ValueError` (thông điệp có mẫu `!schedule mon,fri 08:30`) khi sai định dạng.
  - `format_days_vi(days: str) -> str` — `"mon,fri"` → `"Thứ 2, Thứ 6"`; `"sun"` → `"Chủ nhật"`.
  - Hằng `_DAY_NAMES: list[str]` (index 0=mon…6=sun) và `_DAY_VI: dict[str, str]`.

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_scheduler.py`:

```python
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
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `python -m pytest tests/test_scheduler.py -q`
Expected: FAIL — `ImportError: cannot import name 'parse_schedule'`.

- [ ] **Step 3: Cài đặt tối thiểu**

Trong `agent/scheduler/__init__.py`, ngay sau các dòng `import` (trước `_scheduler: ... = None`), thêm:

```python
import re

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
```

- [ ] **Step 4: Chạy test để xác nhận pass**

Run: `python -m pytest tests/test_scheduler.py -q`
Expected: PASS toàn bộ.

- [ ] **Step 5: Commit**

```bash
git add agent/scheduler/__init__.py tests/test_scheduler.py
git commit -m "feat(scheduler): add parse_schedule and format_days_vi pure helpers"
```

---

## Task 3: init_scheduler đọc DB→env + hàm reschedule

**Files:**
- Modify: `agent/scheduler/__init__.py` (sửa `init_scheduler`; thêm `reschedule`)
- Test: `tests/test_scheduler.py`

**Interfaces:**
- Consumes: `get_setting` (Task 1); `parse_schedule` (Task 2); `_DAY_NAMES`, `CronTrigger`.
- Produces:
  - `init_scheduler(crawl_and_report_fn) -> BackgroundScheduler` — đọc lịch DB (`schedule_days`, `schedule_time`) → fallback `.env` (`REPORT_SCHEDULE_DAY`, `REPORT_SCHEDULE_TIME`) → mặc định `mon`/`08:00`. Timezone từ `.env`.
  - `reschedule(days: str, time_str: str) -> str` — cập nhật job `weekly_report` bằng `CronTrigger` mới, trả chuỗi lần chạy kế tiếp (dùng `get_next_run()`).

- [ ] **Step 1: Viết test thất bại**

Thêm vào `tests/test_scheduler.py`:

```python
from agent.scheduler import init_scheduler, reschedule, get_next_run, stop
from agent.storage.database import init_db, set_setting


@pytest.fixture
def stop_scheduler_after():
    yield
    stop()


def _noop():
    pass


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
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `python -m pytest tests/test_scheduler.py -q -k "init_scheduler or reschedule"`
Expected: FAIL — `ImportError: cannot import name 'reschedule'` (và init_scheduler chưa đọc DB).

- [ ] **Step 3: Cài đặt tối thiểu**

Thay thế toàn bộ hàm `init_scheduler` hiện tại bằng phiên bản đọc DB→env, và thêm `reschedule`. Thêm import `get_setting` ở đầu file:

```python
from agent.storage.database import get_setting
```

`init_scheduler` mới (thay cho dòng 8-30 cũ):

```python
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
```

Thêm `reschedule` (sau `get_next_run`):

```python
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
```

- [ ] **Step 4: Chạy test để xác nhận pass**

Run: `python -m pytest tests/test_scheduler.py -q`
Expected: PASS toàn bộ.

- [ ] **Step 5: Commit**

```bash
git add agent/scheduler/__init__.py tests/test_scheduler.py
git commit -m "feat(scheduler): read schedule from DB with env fallback + runtime reschedule"
```

---

## Task 4: Phân quyền admin — is_admin + ADMIN_USERNAMES

**Files:**
- Modify: `agent/bot/commands.py` (thêm hàm `is_admin`)
- Modify: `agent/.env.example` (thêm `ADMIN_USERNAMES`)
- Test: `tests/test_commands.py`

**Interfaces:**
- Produces: `is_admin(sender_name: str) -> bool` — so khớp `sender_name` (đã bỏ `@`) với `ADMIN_USERNAMES` (ngăn cách bằng phẩy), không phân biệt hoa/thường. Danh sách rỗng/không cấu hình → luôn `False`.

- [ ] **Step 1: Viết test thất bại**

Thêm vào cuối `tests/test_commands.py`:

```python
def test_is_admin_true_when_listed(monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAMES", "tienpc1,sep_a")
    from agent.bot.commands import is_admin
    assert is_admin("tienpc1") is True


def test_is_admin_case_insensitive(monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAMES", "TienPC1")
    from agent.bot.commands import is_admin
    assert is_admin("tienpc1") is True


def test_is_admin_false_when_not_listed(monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAMES", "sep_a")
    from agent.bot.commands import is_admin
    assert is_admin("tienpc1") is False


def test_is_admin_false_when_unset(monkeypatch):
    monkeypatch.delenv("ADMIN_USERNAMES", raising=False)
    from agent.bot.commands import is_admin
    assert is_admin("tienpc1") is False
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `python -m pytest tests/test_commands.py -q -k is_admin`
Expected: FAIL — `ImportError: cannot import name 'is_admin'`.

- [ ] **Step 3: Cài đặt tối thiểu**

Thêm `import os` vào đầu `agent/bot/commands.py` (nếu chưa có — hiện chưa có), và thêm hàm `is_admin` (sau `SOURCES`):

```python
def is_admin(sender_name: str) -> bool:
    raw = os.getenv("ADMIN_USERNAMES", "")
    admins = {u.strip().lower() for u in raw.split(",") if u.strip()}
    return sender_name.strip().lstrip("@").lower() in admins if admins else False
```

Thêm vào `agent/.env.example`, ngay dưới block Scheduler:

```
# Danh sách username (ngăn cách bằng phẩy) được phép đổi lịch qua lệnh !schedule
ADMIN_USERNAMES=tienpc1
```

- [ ] **Step 4: Chạy test để xác nhận pass**

Run: `python -m pytest tests/test_commands.py -q -k is_admin`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/bot/commands.py agent/.env.example
git commit -m "feat(bot): add is_admin helper and ADMIN_USERNAMES config"
```

---

## Task 5: Lệnh bot !schedule (+ thread sender_name, help)

**Files:**
- Modify: `agent/bot/commands.py` (thread `sender_name` vào `_handle_command`; thêm nhánh `!schedule`; thêm `_handle_schedule`; cập nhật `_help_text`)
- Test: `tests/test_commands.py`

**Interfaces:**
- Consumes: `parse_schedule`, `format_days_vi`, `reschedule`, `get_next_run` (scheduler); `get_setting`, `set_setting` (storage); `is_admin` (Task 4).
- Produces: nhánh lệnh `!schedule`/`!lịch` trong `_handle_command`; chữ ký mới `_handle_command(text, channel_id, rest_client, sender_name, allow_chat_fallback=False)`.

- [ ] **Step 1: Viết test thất bại**

Thêm vào cuối `tests/test_commands.py`:

```python
def test_schedule_view_shows_current(monkeypatch):
    init_db()
    from agent.storage.database import set_setting
    set_setting("schedule_days", "mon,fri")
    set_setting("schedule_time", "08:30")
    rest = make_rest()
    post = make_post("!schedule")
    with patch("agent.bot.commands.get_next_run", return_value="2026-07-17 08:30"):
        handle_post(post, rest, group_event(sender="@ai_ai"))
    msg = rest.post_message.call_args[0][0]
    assert "Thứ 2, Thứ 6" in msg
    assert "08:30" in msg


def test_schedule_set_success_for_admin(monkeypatch):
    init_db()
    monkeypatch.setenv("ADMIN_USERNAMES", "tienpc1")
    rest = make_rest()
    post = make_post("!schedule mon,fri 08:30")
    with patch("agent.bot.commands.reschedule", return_value="2026-07-17 08:30") as resched:
        handle_post(post, rest, group_event(sender="@tienpc1"))
    resched.assert_called_once_with("mon,fri", "08:30")
    from agent.storage.database import get_setting
    assert get_setting("schedule_days") == "mon,fri"
    assert get_setting("schedule_time") == "08:30"
    assert "✅" in rest.post_message.call_args[0][0]


def test_schedule_set_denied_for_non_admin(monkeypatch):
    init_db()
    monkeypatch.setenv("ADMIN_USERNAMES", "tienpc1")
    rest = make_rest()
    post = make_post("!schedule mon,fri 08:30")
    with patch("agent.bot.commands.reschedule") as resched:
        handle_post(post, rest, group_event(sender="@nguoi_la"))
    resched.assert_not_called()
    from agent.storage.database import get_setting
    assert get_setting("schedule_days") is None
    assert "⛔" in rest.post_message.call_args[0][0]


def test_schedule_bad_syntax_shows_hint(monkeypatch):
    init_db()
    monkeypatch.setenv("ADMIN_USERNAMES", "tienpc1")
    rest = make_rest()
    post = make_post("!schedule funday 99:99")
    with patch("agent.bot.commands.reschedule") as resched:
        handle_post(post, rest, group_event(sender="@tienpc1"))
    resched.assert_not_called()
    assert "!schedule" in rest.post_message.call_args[0][0]


def test_help_lists_schedule():
    init_db()
    rest = make_rest()
    handle_post(make_post("!help"), rest, group_event())
    assert "!schedule" in rest.post_message.call_args[0][0]
```

- [ ] **Step 2: Chạy test để xác nhận fail**

Run: `python -m pytest tests/test_commands.py -q -k schedule`
Expected: FAIL — hiện `!schedule` rơi vào `_help_text`, các assert `✅`/`⛔`/`Thứ 2` sai.

- [ ] **Step 3: Cài đặt tối thiểu**

Trong `agent/bot/commands.py`:

3a. Cập nhật import đầu file:

```python
from agent.storage.database import (
    get_recent_items, save_report, save_uploaded_doc, get_last_crawl_time,
    get_setting, set_setting,
)
from agent.scheduler import (
    get_next_run, reschedule, parse_schedule, format_days_vi,
)
```

3b. Trong `handle_post`, sửa lời gọi `_handle_command` (dòng ~47) để truyền `sender_name`:

```python
    if text.startswith("!"):
        _handle_command(
            text, channel_id, rest_client, sender_name,
            allow_chat_fallback=is_dm or mentioned,
        )
        return
```

3c. Sửa chữ ký + thêm nhánh trong `_handle_command`:

```python
def _handle_command(text: str, channel_id: str, rest_client, sender_name: str = "",
                    allow_chat_fallback: bool = False) -> None:
    cmd = text.lower().split()[0]
    if cmd in ("!report", "!báo_cáo"):
        _handle_report(channel_id, rest_client)
    elif cmd == "!status":
        _handle_status(channel_id, rest_client)
    elif cmd in ("!schedule", "!lịch"):
        _handle_schedule(text, channel_id, rest_client, sender_name)
    elif cmd == "!sources":
        rest_client.post_message(_sources_text(), channel_id)
    elif cmd == "!help":
        rest_client.post_message(_help_text(), channel_id)
    elif allow_chat_fallback:
        reply = chat_reply(text, "", rest_client.get_my_username())
        rest_client.post_message(reply, channel_id)
    else:
        rest_client.post_message(_help_text(), channel_id)
```

3d. Thêm hàm `_handle_schedule` (sau `_handle_status`):

```python
def _handle_schedule(text: str, channel_id: str, rest_client, sender_name: str) -> None:
    parts = text.split()
    # Xem lịch: !schedule (không tham số) — ai cũng gọi được
    if len(parts) < 3:
        days = get_setting("schedule_days") or os.getenv("REPORT_SCHEDULE_DAY", "mon")
        time_str = get_setting("schedule_time") or os.getenv("REPORT_SCHEDULE_TIME", "08:00")
        try:
            days_vi = format_days_vi(days)
        except (KeyError, AttributeError):
            days_vi = days
        rest_client.post_message(
            f"🗓️ Lịch hiện tại: {days_vi} lúc {time_str}.\n"
            f"Lần chạy kế tiếp: {get_next_run()}\n"
            "Đổi lịch (admin): !schedule mon,fri 08:30",
            channel_id,
        )
        return

    # Đặt lịch: validate trước, kiểm quyền sau
    try:
        days, time_str = parse_schedule(parts[1], parts[2])
    except ValueError as e:
        rest_client.post_message(f"⚠️ {e}", channel_id)
        return

    if not is_admin(sender_name):
        rest_client.post_message(
            "⛔ Chỉ admin mới đổi được lịch. Bạn vẫn có thể xem bằng `!schedule`.",
            channel_id,
        )
        return

    set_setting("schedule_days", days)
    set_setting("schedule_time", time_str)
    try:
        next_run = reschedule(days, time_str)
    except Exception as e:
        rest_client.post_message(f"⚠️ Lỗi đổi lịch: {e}", channel_id)
        return
    rest_client.post_message(
        f"✅ Đã đổi lịch: {format_days_vi(days)} lúc {time_str}. "
        f"Lần chạy kế tiếp: {next_run}",
        channel_id,
    )
```

3e. Cập nhật `_help_text` — thêm dòng `!schedule` sau dòng `!status`:

```python
        "  `!status` — Thời gian crawl cuối + lịch tiếp theo\n"
        "  `!schedule` — Xem lịch; admin: `!schedule mon,fri 08:30` để đổi\n"
```

- [ ] **Step 4: Chạy test để xác nhận pass**

Run: `python -m pytest tests/test_commands.py -q`
Expected: PASS toàn bộ (kể cả các test cũ — chữ ký `_handle_command` có default nên không vỡ).

- [ ] **Step 5: Commit**

```bash
git add agent/bot/commands.py tests/test_commands.py
git commit -m "feat(bot): add !schedule command for admins to edit crawl schedule at runtime"
```

---

## Task 6: Cập nhật tài liệu người dùng

**Files:**
- Modify: `TIEN_DO_DU_AN.md`
- Modify: `HUONG_DAN_SU_DUNG_NEWBIE.md`

**Interfaces:** không có code; chỉ tài liệu.

- [ ] **Step 1: Đọc 2 file để nắm cấu trúc hiện tại**

Run: mở `TIEN_DO_DU_AN.md` và `HUONG_DAN_SU_DUNG_NEWBIE.md`, tìm mục liệt kê lệnh bot / tính năng.

- [ ] **Step 2: Ghi tính năng mới**

- Trong `TIEN_DO_DU_AN.md`: thêm dòng vào phần "đã xong"/changelog: *"Chỉnh lịch crawl runtime qua lệnh `!schedule` (chỉ admin, lưu DB, không cần restart)."*
- Trong `HUONG_DAN_SU_DUNG_NEWBIE.md`: thêm mục hướng dẫn:
  - `!schedule` — xem lịch hiện tại + lần chạy kế tiếp (ai cũng dùng được).
  - `!schedule mon,fri 08:30` — đổi lịch (chỉ admin trong `ADMIN_USERNAMES`). Ngày: `mon`–`sun` hoặc `0`–`6`, nhiều ngày ngăn cách bằng phẩy; giờ `HH:MM`.
  - Nhắc admin cấu hình `ADMIN_USERNAMES` trong `.env` trên server.

- [ ] **Step 3: Chạy lại toàn bộ test (đảm bảo không vỡ gì)**

Run: `python -m pytest tests/ -q`
Expected: PASS toàn bộ.

- [ ] **Step 4: Commit**

```bash
git add TIEN_DO_DU_AN.md HUONG_DAN_SU_DUNG_NEWBIE.md
git commit -m "docs: document !schedule command and ADMIN_USERNAMES config"
```

---

## Self-Review

**Spec coverage:**
- §1 bảng `settings` + get/set_setting → Task 1 ✅
- §2 scheduler DB→.env + `reschedule` → Task 3 ✅ (`get_next_run`, `stop` giữ nguyên)
- §3 `parse_schedule` + `format_days_vi` → Task 2 ✅
- §4 `ADMIN_USERNAMES` + `is_admin` → Task 4 ✅
- §5 lệnh `!schedule`/`!lịch`, thread `sender_name`, cập nhật help → Task 5 ✅
- Xử lý lỗi (sai cú pháp, không admin, reschedule lỗi) → Task 5 ✅ (`ADMIN_USERNAMES` rỗng → `is_admin` False → nhánh từ chối; thông điệp gợi ý xem lịch)
- Tài liệu (`.env.example`, `TIEN_DO_DU_AN.md`, hướng dẫn) → Task 4 (.env.example) + Task 6 ✅

**Type consistency:** `parse_schedule` trả `(days, time_str)` dùng nhất quán ở Task 3 (`reschedule`) và Task 5. `format_days_vi(days)` nhận chuỗi tên ngày nhất quán. `is_admin(sender_name)` khớp Task 4↔5. `get_setting`/`set_setting` chữ ký khớp Task 1↔3↔5.

**Placeholder scan:** không còn TODO/TBD; mọi step có code hoặc lệnh cụ thể.

**Lưu ý cho người thực thi:** chạy `python -m pytest tests/ -q` **xanh hết** trước mỗi commit (quy tắc CLAUDE.md). `ADMIN_USERNAMES` chưa cấu hình trên server thì không ai đổi được lịch — cần thêm vào `.env` server và restart một lần để nạp biến.
