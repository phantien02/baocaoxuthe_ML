# CLAUDE.md — Bối cảnh dự án cho Claude Code

Bot Netchat tự động báo cáo xu thế công nghệ mạng lõi (crawl RSS → Gemini viết báo cáo → gửi channel) + chat tự nhiên qua DM/@mention. Chủ dự án là kỹ sư mạng core viễn thông, KHÔNG code — giải thích bằng tiếng Việt, dễ hiểu, khi chạm khái niệm phần mềm mới thì giải thích ngắn.

## Đọc gì trước khi làm việc

1. `TIEN_DO_DU_AN.md` — trạng thái hiện tại, backlog, việc đang dở. **Cập nhật file này sau mỗi thay đổi đáng kể.**
2. `HUONG_DAN_DEV.md` — quy trình dev + các cạm bẫy đã gặp (đọc mục "BẮT BUỘC phải biết").
3. `LLD.md` — kiến trúc, module, luồng dữ liệu.

## Hiện trạng vận hành

- Bot chạy production trên **server GCP 35.247.154.93** (`/opt/apps/baocaoxuthe`, container `baocaoxuthe-agent`). Deploy/vận hành: xem `HUONG_DAN_DEPLOY_SERVER.md`.
- Docker local trên máy trạm công ty đã TẮT chủ đích (tránh 2 bot trả lời trùng) — đừng tự bật lại khi bot server đang chạy.
- Repo: https://github.com/phantien02/baocaoxuthe_ML (nhánh `master`).

## Quy tắc bắt buộc

- `python -m pytest tests/ -q` phải xanh hết trước khi commit. Commit theo conventional commits.
- KHÔNG BAO GIỜ commit `.env` hoặc dán token/API key thật vào code, `.env.example`, tài liệu.
- REST Netchat với Bot Token → domain `NETCHAT_BOT_URL` (bot-netchat); WebSocket → `NETCHAT_URL`. Nhầm là 403.
- HTTP tới Netchat phải qua session của `NetchatRestClient` (đã set User-Agent lách WAF) — không gọi `requests` trần.
- Đổi schema DB: sửa CREATE TABLE **và** thêm ALTER TABLE migration trong `init_db()` (DB cũ nằm trong volume).

## Đặc thù môi trường

- Máy trạm công ty (Viettel): WAF chặn UA `python-requests`/PowerShell/Postman (403 HTML); outbound port 22 bị chặn → thao tác server bằng script dán vào GCP browser SSH. Máy ở nhà: không bị các hạn chế này, SSH thẳng tới server được.
- Bot Token bị whitelist endpoint (`api.bot.endpoint_not_allowed`) — endpoint mới phải test bằng curl trước, xem `HUONG_DAN_TEST_API_NETCHAT.md`.
