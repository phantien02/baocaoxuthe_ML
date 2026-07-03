# HƯỚNG DẪN CHO DEV

> Dành cho người biết Python/Git/Docker cơ bản. Đọc kèm `LLD.md` để hiểu kiến trúc.

## Setup nhanh

```bash
git clone https://github.com/phantien02/baocaoxuthe_ML.git
cd baocaoxuthe_ML
cp .env.example .env        # điền giá trị thật — xem bảng biến trong README.md
pip install -r requirements.txt
python -m pytest tests/ -q  # phải 69 passed trước khi làm gì tiếp
```

Chạy local không Docker (cần set env từ `.env` thủ công, đổi `DB_PATH` sang đường dẫn Windows):

```bash
python -m agent.main
```

Chạy chuẩn bằng Docker (tự nạp `.env`, DB nằm ở volume `agent_data:/data`):

```bash
docker compose up -d --build
docker logs -f baocaoxuthe-agent
```

## Các điểm BẮT BUỘC phải biết (đặc thù môi trường Viettel)

1. **Hai domain Netchat, không được nhầm:**
   - REST với Bot Token → `NETCHAT_BOT_URL` (`bot-netchat.viettel.vn`). Gọi nhầm domain người dùng → 403 "API bot phải được gọi qua BMS".
   - WebSocket → `NETCHAT_URL` (`netchat.viettel.vn`).
2. **WAF nội bộ chặn theo User-Agent.** `python-requests`, PowerShell, Postman đều bị 403 trả trang HTML. `rest_client.py` đã đặt UA `curl/8.4.0` (đổi qua env `NETCHAT_USER_AGENT`). Khi thêm HTTP call mới tới Netchat, dùng session của `NetchatRestClient`, đừng gọi `requests` trần.
3. **Bot Token bị whitelist endpoint.** Một số API chuẩn Mattermost bị chặn với bot (`api.bot.endpoint_not_allowed`), ví dụ `/channels/name/{team}/{name}`. Cần channel_id thì dùng `/users/me/channels`. Khi thêm endpoint mới → test bằng curl trước (xem `HUONG_DAN_TEST_API_NETCHAT.md`).
4. **API chỉ nhận ID 26 ký tự**, không nhận username/tên channel. Luôn tra ID trước.
5. **Test bằng curl phải chạy từ cmd.exe hoặc Git Bash** — PowerShell/Postman bị WAF chặn.

## Quy trình phát triển

1. Viết/sửa test trước hoặc song song với code (`tests/` dùng pytest + `responses` để mock HTTP, `unittest.mock` cho rest_client).
2. `python -m pytest tests/ -q` — xanh hết mới đi tiếp.
3. Test tích hợp thật trong container:
   ```bash
   docker compose up -d --build
   docker exec baocaoxuthe-agent python -c "from agent.bot.rest_client import NetchatRestClient; c=NetchatRestClient(); print(c.get_my_user_id())"
   ```
4. Commit theo conventional commits (`feat:`, `fix:`, `docs:`...), cập nhật `TIEN_DO_DU_AN.md` nếu thay đổi đáng kể.
5. **Không bao giờ commit `.env`** (đã gitignore) và không dán token thật vào `.env.example`/tài liệu.

## Các việc hay làm

**Thêm nguồn crawl mới** — ưu tiên RSS (có pubDate):

1. Tạo `agent/crawler/source_<ten>.py`, kế thừa `BaseCrawler`:
   - Có RSS: chỉ cần `FEED_URL` + gọi `self._fetch_rss_items(self.FEED_URL)` trong `crawl()` (xem `source_3gpp.py`).
   - Chỉ có HTML: parse BeautifulSoup, tự set `date` nếu trang có (xem `source_nokia.py`).
2. Đăng ký vào `CRAWLERS` trong `agent/crawler/__init__.py`.
3. Thêm test vào `tests/test_crawlers.py` (mock feed bằng `responses`).

**Thêm lệnh bot mới:** sửa `_handle_command()` trong `agent/bot/commands.py` + cập nhật `_help_text()` + test trong `tests/test_commands.py`.

**Sửa prompt LLM:** tất cả nằm ở `agent/llm/prompts.py` (`REPORT_PROMPT`, `SUMMARIZE_PROMPT`, `CHAT_PROMPT`).

**Đổi schema DB:** sửa `init_db()` trong `agent/storage/database.py` — CREATE TABLE cho DB mới **và** khối ALTER TABLE migration cho DB cũ (volume Docker giữ DB qua các lần build; xem mẫu cột `published_at`).

**Chạy tay báo cáo theo khoảng ngày** (backfill):

```bash
docker exec -w /app -e PYTHONPATH=/app baocaoxuthe-agent python - <<'EOF'
from agent.storage.database import init_db, get_items_between, save_report
from agent.llm.claude_client import generate_report
from agent.bot.rest_client import NetchatRestClient
init_db(); rest = NetchatRestClient(); cid = rest.get_channel_id()
items = get_items_between("2026-06-01", "2026-06-08")
if items:
    rep = generate_report(items, "Tuần 1 tháng 6/2026")
    save_report("manual-backfill", rep, cid); rest.post_message(rep, cid)
EOF
```

## Cạm bẫy đã gặp (đừng dẫm lại)

- `post["type"]` là **loại bài đăng** (system_join_channel...), KHÔNG phải loại channel. Loại channel (`D`/`P`/`O`) nằm trong `event_data["channel_type"]` của WebSocket event.
- `file_id` chỉ gắn được vào đúng **1 post**, và post phải **cùng channel** với lúc upload.
- Tối đa **5 file/post** (`MAX_FILES_PER_POST`).
- SQLite cột TIMESTAMP trả về `datetime` object (do `PARSE_DECLTYPES`), không phải string — cẩn thận khi slice/so sánh.
- Gemini thỉnh thoảng 503 — code chạy tay cần retry; TODO: đưa retry vào luồng scheduler.
- Chạy script trong container: cần `-w /app -e PYTHONPATH=/app` nếu script nằm ngoài `/app`.
