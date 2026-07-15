# Thiết kế: Chỉnh lịch crawl/báo cáo qua lệnh bot (runtime, chỉ admin)

Ngày: 2026-07-15

## Vấn đề

Lịch crawl + gửi báo cáo hiện cố định trong `.env` (`REPORT_SCHEDULE_DAY`,
`REPORT_SCHEDULE_TIME`, `REPORT_TIMEZONE`) và chỉ được đọc **một lần lúc khởi
động** trong `agent/scheduler/__init__.py`. Muốn đổi lịch phải sửa `.env` rồi
restart container trên server — bất tiện cho chủ dự án (không code, tương tác
với bot qua Netchat).

## Mục tiêu

Cho phép đổi lịch crawl/báo cáo **ngay lúc chạy** qua lệnh bot trong Netchat,
không cần restart. Lịch mới được lưu bền vững (không mất khi restart).

## Phạm vi (đã chốt với chủ dự án)

- Chỉnh qua **lệnh bot** trong Netchat (không làm web quản trị, không dừng ở
  sửa `.env`).
- Kiểu lịch: **thứ trong tuần + giờ**, cho phép **nhiều ngày/tuần** (vd `mon,fri`).
- **Chỉ admin** được đổi lịch; xem lịch thì ai cũng được.

Ngoài phạm vi (YAGNI): lịch lặp theo khoảng (mỗi N giờ), nhiều lịch song song,
đổi timezone qua lệnh, web quản trị.

## Kiến trúc & thành phần

### 1. Lưu cấu hình vào DB — `agent/storage/database.py`

Thêm bảng key-value:

```sql
CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Thêm vào `init_db()` (dùng `CREATE TABLE IF NOT EXISTS`, không cần ALTER vì là
bảng mới). Hai hàm mới:

- `get_setting(key: str, default: str | None = None) -> str | None`
- `set_setting(key: str, value: str) -> None` (UPSERT, cập nhật `updated_at`).

Lịch lưu ở 2 khóa:
- `schedule_days` — chuỗi ngày, vd `"mon,fri"`.
- `schedule_time` — `"HH:MM"`, vd `"08:30"`.

### 2. Scheduler đọc/ghi runtime — `agent/scheduler/__init__.py`

- `init_scheduler(fn)`: đọc lịch theo thứ tự ưu tiên **DB → .env → mặc định
  code**. Nếu DB chưa có khóa lịch, dùng giá trị `.env` như hiện tại (không phá
  hành vi cũ). Timezone vẫn lấy từ `.env` (`REPORT_TIMEZONE`).
- `reschedule(days: str, time_str: str) -> str`: cập nhật job `weekly_report`
  đang chạy bằng trigger cron mới (dùng `_scheduler.reschedule_job` hoặc
  remove + add với `replace_existing=True`). Trả về chuỗi mô tả lần chạy kế
  tiếp. Không đụng tới DB (việc lưu DB do lớp lệnh gọi trước đó).
- `get_next_run()`, `stop()`: giữ nguyên.

`day_of_week` của APScheduler nhận chuỗi nhiều ngày ngăn cách bằng phẩy
(`"mon,fri"`) hoặc số (`0`–`6`), nên truyền thẳng chuỗi `days` đã chuẩn hóa vào
`CronTrigger(day_of_week=...)`.

### 3. Parse & validate lịch — hàm thuần (dễ test)

Đặt trong `agent/scheduler/__init__.py` (hoặc module con) một hàm thuần:

- `parse_schedule(days_arg: str, time_arg: str) -> tuple[str, str]`
  - `days_arg`: tách theo phẩy, mỗi token phải thuộc
    `{mon,tue,wed,thu,fri,sat,sun}` (không phân biệt hoa/thường) hoặc số `0`–`6`.
    Chuẩn hóa về chữ thường. Loại trùng, giữ thứ tự.
  - `time_arg`: khớp `HH:MM`, `0<=HH<=23`, `0<=MM<=59`.
  - Sai định dạng → raise `ValueError` với thông điệp gợi ý cú pháp.
- `format_days_vi(days: str) -> str`: đổi `"mon,fri"` → `"Thứ 2, Thứ 6"` để hiển
  thị thân thiện (chủ nhật = "Chủ nhật").

### 4. Phân quyền admin — `.env` + helper

- Thêm biến `.env`: `ADMIN_USERNAMES` (danh sách username ngăn cách bằng phẩy,
  vd `tienpc1,sep_a`). Thêm dòng minh họa vào `.env.example`.
- Helper `is_admin(sender_name: str) -> bool` (trong `commands.py`): so khớp
  `sender_name` (đã bỏ `@`) với danh sách, không phân biệt hoa/thường. Danh sách
  rỗng → không ai là admin (an toàn mặc định); bot báo rõ chưa cấu hình admin.

### 5. Lệnh bot — `agent/bot/commands.py`

Trong `_handle_command`, thêm nhánh lệnh `!schedule` với alias `!lịch` (theo
đúng pattern `!report`/`!báo_cáo` sẵn có). Cần truyền `sender_name` xuống
`_handle_command` (hiện chưa có) để kiểm tra admin.

- `!schedule` (không tham số): trả về lịch hiện tại (đọc DB, fallback .env) +
  lần chạy kế tiếp (`get_next_run()`). Ai cũng gọi được.
- `!schedule <days> <time>`: 
  1. `parse_schedule` → nếu `ValueError`, trả cú pháp mẫu.
  2. `is_admin(sender_name)` → nếu không, từ chối lịch sự.
  3. `set_setting("schedule_days", ...)`, `set_setting("schedule_time", ...)`.
  4. `reschedule(days, time)`.
  5. Trả lời: `✅ Đã đổi lịch: <format_days_vi> lúc <time>. Lần chạy kế tiếp: <next_run>`.

Cập nhật `_help_text()` thêm dòng `!schedule`.

## Luồng dữ liệu

Khởi động: `init_db()` → `init_scheduler()` đọc lịch (DB → .env) → tạo job.

Đổi lịch: user gõ `!schedule mon,fri 08:30` → `parse_schedule` (validate) →
`is_admin` → `set_setting` (lưu DB) → `reschedule` (đổi job đang chạy) → bot xác
nhận + báo lần chạy kế tiếp.

Restart sau đó: `init_scheduler` đọc lại từ DB → giữ đúng lịch user đã đặt.

## Xử lý lỗi

- Sai định dạng ngày/giờ → bot trả cú pháp mẫu: `!schedule mon,fri 08:30`.
- Không phải admin → `⛔ Chỉ admin mới đổi được lịch.` (kèm gợi ý xem lịch).
- `ADMIN_USERNAMES` rỗng → báo chưa cấu hình admin, hướng dẫn thêm vào `.env`.
- Lỗi khi reschedule → log + báo lỗi ngắn gọn cho user; không làm crash bot.

## Kiểm thử (theo pattern `tests/` hiện có)

- `parse_schedule`: hợp lệ (1 ngày, nhiều ngày, số 0–6, hoa/thường), lỗi (ngày
  sai, giờ sai, thiếu tham số).
- `format_days_vi`: map đúng thứ 2..CN.
- `get_setting`/`set_setting`: ghi rồi đọc lại, UPSERT ghi đè.
- `init_scheduler` ưu tiên DB hơn `.env`; `reschedule` đổi được `next_run_time`
  của job.
- `is_admin`: có/không trong danh sách, không phân biệt hoa/thường, danh sách rỗng.
- `_handle_command` với fake rest_client: xem lịch, đặt lịch thành công (admin),
  bị từ chối (không admin), sai cú pháp.

## Tài liệu cần cập nhật (khi implement)

- `.env.example`: thêm `ADMIN_USERNAMES`.
- `TIEN_DO_DU_AN.md`: ghi tính năng mới.
- `HUONG_DAN_SU_DUNG_NEWBIE.md` / README: hướng dẫn lệnh `!schedule`.
