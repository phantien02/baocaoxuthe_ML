# LOW-LEVEL DESIGN (LLD) — Agent Báo cáo Xu thế Mạng lõi

> Phiên bản 1.0 — 03/07/2026.
> Tài liệu thiết kế chi tiết, viết cho kỹ sư viễn thông đọc để hiểu cấu trúc phần mềm.
> Mỗi khái niệm phần mềm mới đều có giải thích ngắn, kèm liên tưởng sang hệ thống mạng khi phù hợp.

## 1. Bài toán và phạm vi

Hệ thống là một **agent** (chương trình chạy nền, tự hành) làm 2 việc:

1. **Chủ động theo lịch:** hàng tuần crawl tin từ các nguồn công nghệ mạng lõi → nhờ LLM
   (mô hình ngôn ngữ lớn — Google Gemini) viết báo cáo xu thế → gửi vào channel netChat.
2. **Bị động theo sự kiện:** lắng nghe tin nhắn trên netChat 24/7 và phản hồi
   (lệnh `!report`..., chat tự nhiên, tóm tắt file đính kèm).

Có thể liên tưởng: giống một node mạng vừa có **scheduled job** (như job đo kiểm KPI hàng đêm)
vừa có **event-driven signaling** (như xử lý bản tin SIP đến bất kỳ lúc nào).

## 2. Kiến trúc tổng thể

```
                    ┌───────────────────────────── Docker container ─────────────────────────────┐
                    │                                                                            │
  Internet          │   agent/crawler/          agent/llm/              agent/scheduler/         │
┌──────────┐  RSS/  │  ┌───────────────┐      ┌────────────────┐      ┌────────────────┐        │
│ 3GPP,GSMA│ HTTP   │  │ 6 crawler     │      │ Gemini client   │      │ APScheduler    │        │
│ ETSI,... ├────────┼─►│ (RSS + HTML)  │      │ (report/chat/   │      │ (cron hàng     │        │
└──────────┘        │  └──────┬────────┘      │  summarize)     │      │  tuần)         │        │
                    │         │ lưu           └───────▲────────┘      └───────┬────────┘        │
                    │         ▼                       │ gọi                    │ kích hoạt       │
                    │  ┌───────────────┐              │                        ▼                 │
                    │  │ agent/storage │      ┌───────┴────────────────────────────────┐        │
                    │  │ SQLite (/data)│◄─────┤              agent/main.py             │        │
                    │  └───────────────┘      │        (điểm khởi động, ghép nối)      │        │
                    │                         └───────┬───────────────────▲────────────┘        │
                    │                                 │                   │                     │
                    │                         ┌───────▼───────┐   ┌───────┴────────┐            │
  Mạng nội bộ       │                         │ rest_client   │   │ websocket_     │            │
┌──────────────┐    │                         │ (gửi tin/file)│   │ client (nhận   │            │
│   netChat    │◄───┼─────────────────────────┤ REST API      │   │ tin realtime)  │            │
│  (Mattermost)│    │   bot-netchat.viettel.vn└───────────────┘   └───────▲────────┘            │
└──────┬───────┘    │                                                     │                     │
       │            │       netchat.viettel.vn (WebSocket) ───────────────┘                     │
       ▼            │                         ┌────────────────┐                                │
   Người dùng       │                         │ bot/commands.py│  ◄── bộ định tuyến tin nhắn    │
                    │                         └────────────────┘                                │
                    └────────────────────────────────────────────────────────────────────────────┘
```

Nguyên tắc thiết kế: **chia lớp theo trách nhiệm** (separation of concerns) — mỗi thư mục
một nhiệm vụ, module này gọi module kia qua hàm, không chồng chéo. Tương tự tách
control plane / user plane: sửa crawler không đụng vào bot, sửa prompt không đụng DB.

## 3. Công nghệ sử dụng và lý do

| Công nghệ | Vai trò | Giải thích cho người mới |
|---|---|---|
| **Python 3.11** | Ngôn ngữ chính | Phổ biến nhất cho AI/automation, thư viện phong phú |
| **Docker + docker-compose** | Đóng gói & chạy | "Container" = máy ảo siêu nhẹ chứa đúng môi trường app cần (Python, thư viện). Chạy đâu cũng giống nhau — như file cấu hình node chuẩn hóa, mang sang site nào cũng lên được |
| **SQLite** | Cơ sở dữ liệu | DB dạng 1 file duy nhất (`/data/agent.db`), không cần cài server DB riêng. Đủ cho quy mô này |
| **requests** | HTTP client | Thư viện gọi REST API (GET/POST như curl nhưng trong code) |
| **websocket-client** | Kênh nhận realtime | WebSocket = kết nối TCP giữ mở 2 chiều, server đẩy tin xuống ngay khi có (như SCTP association giữ heartbeat, khác với REST hỏi-đáp từng lần) |
| **APScheduler** | Lập lịch | Cron trong app: "thứ 2 hàng tuần 08:00 chạy hàm X" |
| **google-genai (Gemini)** | LLM | Gọi API mô hình AI của Google để viết báo cáo/tóm tắt/chat. Model cấu hình qua env |
| **BeautifulSoup4** | Parse HTML | Bóc nội dung từ trang web (crawler Nokia) và làm sạch HTML trong RSS |
| **pypdf / python-docx** | Đọc file | Trích text từ PDF/DOCX người dùng gửi |
| **pytest + responses** | Kiểm thử | `responses` giả lập server HTTP → test không cần mạng thật (như giả lập bản tin trong lab thay vì đấu nối node thật) |

## 4. Chi tiết từng module

### 4.1. `agent/main.py` — điểm khởi động
Khởi tạo DB → tạo `NetchatRestClient` + `NetchatWebSocketClient` → đăng ký lịch tuần
(`crawl_and_report`) → bắt đầu lắng nghe WebSocket → giữ tiến trình sống.
Bắt tín hiệu SIGTERM/SIGINT để tắt sạch (graceful shutdown).

### 4.2. `agent/bot/rest_client.py` — gửi (chiều đi)
Đóng gói toàn bộ REST API netChat. Điểm kỹ thuật đáng chú ý:
- **Base URL** = `NETCHAT_BOT_URL` (bot token bắt buộc qua domain bot — ràng buộc BMS của Viettel).
- **User-Agent** giả lập curl vì WAF nội bộ chặn UA `python-requests`.
- **Cache trong bộ nhớ** (channel_id, user_id đã tra) — tránh gọi lại API cho dữ liệu không đổi,
  giống DNS cache.
- Luồng DM 3 bước: username → user_id → direct channel → post.
- Gửi file 2 bước: upload multipart lấy `file_id` → tạo post gắn `file_ids` (tối đa 5).

### 4.3. `agent/bot/websocket_client.py` — nhận (chiều về)
Mở WebSocket tới `NETCHAT_URL/api/v4/websocket`, xác thực bằng bản tin
`authentication_challenge` chứa token. Lắng nghe event `posted`; mỗi event chứa
JSON của bài đăng + metadata (loại channel, người gửi, danh sách được mention) →
đẩy về callback. Chạy trong **thread** riêng (luồng song song trong 1 tiến trình)
với `reconnect=5` — tự nối lại khi rớt, như cơ chế re-establish của SCTP.

### 4.4. `agent/bot/commands.py` — bộ định tuyến tin nhắn
"Route" mỗi tin nhắn đến đúng xử lý — vai trò như bảng định tuyến bản tin:

```
tin nhắn đến (event posted)
 ├─ là tin hệ thống / tin của chính bot?  → bỏ qua (chống loop)
 ├─ không phải DM, không được @mention, không phải channel báo cáo? → bỏ qua
 ├─ có file đính kèm?      → tải file, trích text, LLM tóm tắt, trả kết quả
 ├─ bắt đầu bằng "!"?      → chạy lệnh (!report/!status/!sources/!help)
 └─ còn lại (DM hoặc @bot) → LLM chat tự nhiên (CHAT_PROMPT), trả lời vào đúng channel
```

Nhận diện mention: đọc field `mentions` trong event (danh sách user_id) + dự phòng
tìm chuỗi `@username` trong nội dung; bỏ phần `@bot` khỏi câu trước khi đưa cho LLM.

### 4.5. `agent/crawler/` — thu thập dữ liệu
- `base.py`: lớp cha `BaseCrawler` chứa logic dùng chung — **kế thừa** (inheritance):
  lớp con chỉ khai báo URL, mọi xử lý phức tạp nằm một chỗ.
  - `_fetch_rss_items()`: đọc RSS feed (XML), bóc title/link/description/**pubDate**.
    RSS được ưu tiên vì có ngày xuất bản chuẩn (định dạng RFC 822).
  - `_detect_topic()`: phân loại bài theo từ khóa → 5GC / IMS / EPC / Autonomous / General.
- Mỗi nguồn 1 file `source_*.py`. Hiện 3GPP/GSMA/ETSI dùng RSS; Nokia parse HTML;
  Ericsson/Huawei đang hỏng (xem `TIEN_DO_DU_AN.md` mục 4).
- `__init__.py`: gom danh sách `CRAWLERS`, hàm `run_all_crawlers()` chạy tuần tự và lưu DB.
  Chống trùng bằng ràng buộc `UNIQUE` trên cột URL — bài đã có thì INSERT thất bại êm.

### 4.6. `agent/llm/` — tầng AI
- `prompts.py`: 3 khuôn prompt (REPORT / SUMMARIZE / CHAT). Prompt = "kịch bản chỉ đạo"
  cho LLM, quy định vai trò, định dạng đầu ra, ngôn ngữ.
- `claude_client.py`: gọi Gemini API (`generate_content`), giới hạn `max_output_tokens`
  theo từng loại. Client khởi tạo **lazy** (chỉ tạo khi dùng lần đầu) và tái sử dụng.
  (Tên file mang tính lịch sử — trước dùng Claude, đã chuyển sang Gemini.)

### 4.7. `agent/storage/database.py` — dữ liệu
3 bảng SQLite:

| Bảng | Nội dung | Cột đáng chú ý |
|---|---|---|
| `crawled_items` | Bài đã crawl | `url UNIQUE` (chống trùng), `published_at` (ngày xuất bản, có thể NULL), `crawled_at` |
| `reports` | Báo cáo đã tạo | `trigger_type` (scheduled/manual/manual-june-backfill) |
| `uploaded_docs` | File người dùng gửi + tóm tắt | `uploaded_by` |

Truy vấn thời gian dùng `COALESCE(published_at, crawled_at)` — ưu tiên ngày xuất bản,
thiếu thì rơi về ngày crawl. `init_db()` có khối **migration** (ALTER TABLE trong try/except)
để DB cũ trong volume tự nâng cấp schema khi lên phiên bản mới — như bước upgrade
database khi nâng cấp phần mềm node, phải tương thích dữ liệu cũ.

### 4.8. `agent/scheduler/` — lập lịch
APScheduler đăng ký 1 job cron theo `REPORT_SCHEDULE_DAY/TIME/TIMEZONE`.
Đến giờ → `crawl_and_report()`: crawl tất cả nguồn → lấy bài 7 ngày → LLM viết báo cáo
→ lưu bảng `reports` → post lên channel.

## 5. Hai luồng nghiệp vụ chính (sequence)

**Luồng 1 — Báo cáo tuần tự động:**

```
Scheduler ──► run_all_crawlers() ──► [6 nguồn] ──► SQLite (crawled_items)
     └──► get_recent_items(7 ngày) ──► generate_report() ──► Gemini API
              └──► save_report() ──► rest_client.post_message() ──► netChat channel
```

**Luồng 2 — Người dùng nhắn tin:**

```
Người dùng gõ tin ──► netChat server ──► WebSocket event "posted"
  ──► websocket_client (parse JSON) ──► handle_post (định tuyến, mục 4.4)
  ──► [lệnh / chat LLM / tóm tắt file] ──► rest_client.post_message() ──► trả lời
```

## 6. Cấu hình (12-factor config)

Toàn bộ cấu hình qua **biến môi trường** (file `.env`, Docker tự nạp qua `env_file`) —
code không chứa giá trị môi trường/bí mật nào. Đổi channel, đổi model AI, đổi lịch:
chỉ sửa `.env` rồi restart container, không sửa code. Danh sách biến: xem README.md.

## 7. Xử lý lỗi và các ràng buộc đã biết

| Ràng buộc | Cách hệ thống xử lý |
|---|---|
| WAF chặn User-Agent python | UA giả curl trong rest_client (env `NETCHAT_USER_AGENT`) |
| Bot token bị whitelist endpoint | Chỉ dùng endpoint đã kiểm chứng; channel_id tra qua `/users/me/channels` |
| Crawler nguồn chết / đổi giao diện | Mỗi crawler bọc try/except, lỗi 1 nguồn không sập cả phiên crawl |
| Tin nhắn của chính bot dội lại | So user_id người gửi với user_id bot → bỏ qua (chống vòng lặp vô hạn) |
| Gemini 503 khi quá tải | Hiện chưa retry trong luồng tự động (backlog mục 5 TIEN_DO_DU_AN.md) |
| WebSocket rớt | Thư viện tự reconnect mỗi 5 giây |

## 8. Chiến lược kiểm thử

- **Unit test** (69 test, `tests/`): mỗi module test riêng, mọi HTTP đều giả lập bằng
  `responses` (không chạm mạng thật) — chạy được offline, nhanh (~6 giây).
- **Test tích hợp thủ công**: `docker exec` gọi thẳng hàm trong container chạy thật
  (kiểm chứng WAF, whitelist, Gemini) — bắt buộc sau thay đổi liên quan Netchat/LLM
  vì các ràng buộc hạ tầng nội bộ **không thể** mô phỏng trong unit test.
- Nguyên tắc: test xanh hết trước khi commit; bug tìm thấy ở môi trường thật → viết thêm
  test tái hiện (ví dụ các test mention/DM sinh ra từ bug `post["type"]`).

## 9. Triển khai

- `Dockerfile`: image nền `python:3.11-slim` → cài requirements → copy code →
  chạy `python -m agent.main`.
- `docker-compose.yml`: 1 service duy nhất, nạp `.env`, mount **volume** `agent_data:/data`
  (volume = ổ dữ liệu sống lâu hơn container — xóa/build lại container không mất DB),
  `restart: unless-stopped` (rớt là tự dậy).
- Nâng cấp phiên bản: `git pull && docker compose up -d --build` — build image mới,
  thay container, DB giữ nguyên nhờ volume + migration tự chạy.
