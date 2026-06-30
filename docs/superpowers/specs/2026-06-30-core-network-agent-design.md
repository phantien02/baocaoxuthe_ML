# Design Spec: Agent Báo Cáo Kiến Trúc & Công Nghệ Mới — Mạng Lõi

**Date:** 2026-06-30  
**Author:** Kỹ sư Mạng Lõi, Viettel  
**Status:** Approved

---

## 1. Mục tiêu

Xây dựng một agent Python tự động thu thập, tổng hợp và báo cáo các công nghệ mới trong lĩnh vực **Core Network** phục vụ:
- Nghiên cứu xu thế công nghệ
- Hỗ trợ quyết định đầu tư, mua sắm thiết bị

Agent hoạt động như một chatbot trên **Netchat (Viettel)**, giao tiếp qua Mattermost-compatible API.

---

## 2. Phạm vi công nghệ theo dõi

| Domain | Nội dung |
|--------|----------|
| 5G Core (5GC) | AMF, SMF, UPF, PCF, NRF, NWDAF — 3GPP Rel.17/18/19 |
| EPC / 4G Evolution | PGW, SGW, MME, PCRF — xu hướng migration lên 5GC |
| IMS | VoLTE, VoNR, RCS |
| Autonomous Networks | Self-managing core, AI/ML-driven operations, ETSI ZSM |

---

## 3. Kiến trúc — Modular Monolith

Một Docker container duy nhất, code chia module rõ ràng. Các module giao tiếp trực tiếp qua Python (không qua network/message queue).

### 3.1 Cấu trúc thư mục

```
core-network-agent/
├── agent/
│   ├── bot/
│   │   ├── websocket_client.py   # nhận tin từ Netchat qua WebSocket
│   │   └── rest_client.py        # gửi tin/báo cáo qua REST API
│   ├── crawler/
│   │   ├── base.py               # base class, interface chung
│   │   ├── source_3gpp.py
│   │   ├── source_gsma.py
│   │   ├── source_etsi.py
│   │   ├── source_ericsson.py
│   │   ├── source_nokia.py
│   │   └── source_huawei.py
│   ├── llm/
│   │   ├── claude_client.py      # Anthropic Python SDK
│   │   └── prompts.py            # prompt templates (bilingual)
│   ├── scheduler/
│   │   └── __init__.py           # APScheduler weekly cron
│   ├── storage/
│   │   └── database.py           # SQLite via sqlite3
│   └── main.py                   # entrypoint, khởi động tất cả modules
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

### 3.2 Modules

**`bot/`**
- Kết nối Netchat qua WebSocket (`wss://netchat.viettel.vn/api/v4/websocket`)
- Lắng nghe event `posted` để nhận lệnh từ người dùng
- Gửi báo cáo/phản hồi qua REST `POST /api/v4/posts`
- Xử lý file attachment: download → chuyển sang storage
- Trong channel cấu hình: chỉ phản hồi tin nhắn bắt đầu bằng `!` (không cần @mention)
- Trong DM với bot: phản hồi mọi tin nhắn

**`crawler/`**
- Mỗi nguồn là 1 file Python kế thừa `base.BaseCrawler`
- Interface chung: `crawl() -> list[CrawledItem]`
- `CrawledItem`: `{source, title, url, content, topic, date}`
- Deduplication theo URL trước khi lưu storage
- Dùng `requests` + `BeautifulSoup4`

**Nguồn crawl:**
| Source | URL | Topics |
|--------|-----|--------|
| 3GPP | 3gpp.org/specifications | 5GC, IMS, EPC |
| GSMA | gsma.com/solutions-and-impact | 5GC, Autonomous |
| ETSI | etsi.org/technologies | Autonomous (ZSM), NFV |
| Ericsson | ericsson.com/en/blog | All topics |
| Nokia | nokia.com/blog | All topics |
| Huawei | carrier.huawei.com/en/insights | All topics |

**`llm/`**
- Anthropic Python SDK (`anthropic` package)
- Model: `claude-sonnet-4-6` (có thể override qua env var)
- 2 chức năng chính:
  - `generate_report(items)` — tạo báo cáo tuần từ danh sách bài crawl
  - `summarize_document(content, filename)` — tóm tắt tài liệu upload
- Prompt template đảm bảo output song ngữ: tiêu đề/tóm tắt tiếng Việt, nội dung kỹ thuật tiếng Anh

**`scheduler/`**
- APScheduler `BlockingScheduler`
- Cron mặc định: Thứ 2 lúc 08:00 (cấu hình qua env)
- Khi trigger: gọi tất cả crawlers → lưu storage → gọi LLM → gửi Netchat

**`storage/`**
- SQLite, file tại `/data/agent.db` (mount qua Docker volume)
- Schema:

```sql
CREATE TABLE crawled_items (
    id INTEGER PRIMARY KEY,
    source TEXT, title TEXT, url TEXT UNIQUE,
    content TEXT, topic TEXT,
    crawled_at TIMESTAMP, used_in_report BOOLEAN DEFAULT 0
);

CREATE TABLE reports (
    id INTEGER PRIMARY KEY,
    created_at TIMESTAMP,
    trigger_type TEXT,  -- 'scheduled' | 'manual'
    content TEXT,
    sent_to_channel TEXT
);

CREATE TABLE uploaded_docs (
    id INTEGER PRIMARY KEY,
    filename TEXT, file_type TEXT,
    content TEXT, summary TEXT,
    uploaded_at TIMESTAMP, uploaded_by TEXT
);
```

---

## 4. Luồng dữ liệu

### Báo cáo tự động (hàng tuần)
```
Scheduler (cron) 
  → Crawlers (fetch từng source) 
  → Storage (dedup + lưu crawled_items)
  → LLM (generate_report từ items chưa dùng)
  → Storage (lưu report)
  → Bot REST (gửi lên Netchat channel)
```

### On-demand qua chat
```
Netchat user nhắn "!report"
  → Bot WebSocket nhận posted event
  → Gọi LLM với items được crawl trong 7 ngày gần nhất (window mặc định, cấu hình được)
  → Bot REST gửi báo cáo
```

### Upload tài liệu
```
Netchat user attach file (PDF/DOCX)
  → Bot download file qua REST /api/v4/files/{file_id}
  → Storage lưu uploaded_docs
  → LLM summarize_document
  → Bot REST gửi tóm tắt
```

---

## 5. Cấu trúc báo cáo output

```
📡 BÁO CÁO CÔNG NGHỆ MẠNG LÕI — Tuần [W]/[YYYY]

## Tổng quan
[2-3 câu tóm tắt điểm nổi bật tuần bằng tiếng Việt]

## 5G Core (5GC)
### [Title in English]
Source: [source] | [date]
[3-5 sentence technical summary in English]

## IMS / VoNR
...

## Autonomous Networks
...

## EPC / 4G Evolution
...

## 🔗 Tài liệu đáng chú ý
[Danh sách links quan trọng]
```

---

## 6. Giao tiếp Netchat — Bot Commands

| Lệnh | Hành động |
|------|-----------|
| `!report` | Tạo báo cáo ngay (on-demand) |
| `!report week` | Báo cáo từ 7 ngày qua |
| `!status` | Lần crawl cuối, lịch chạy tiếp theo |
| `!sources` | Liệt kê nguồn đang theo dõi |
| `!help` | Danh sách lệnh |
| *(file attachment)* | Tự động tóm tắt PDF/DOCX |

---

## 7. Cấu hình & Biến môi trường

```env
# LLM
CLAUDE_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-6

# Netchat
NETCHAT_URL=https://netchat.viettel.vn
NETCHAT_TOKEN=mm_xxx...
NETCHAT_TEAM_NAME=your-team
NETCHAT_CHANNEL_NAME=core-network-tech

# Scheduler
REPORT_SCHEDULE_DAY=mon
REPORT_SCHEDULE_TIME=08:00
REPORT_TIMEZONE=Asia/Ho_Chi_Minh
```

---

## 8. Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY agent/ ./agent/
VOLUME ["/data"]
CMD ["python", "-m", "agent.main"]
```

### docker-compose.yml
```yaml
services:
  agent:
    build: .
    env_file: .env
    volumes:
      - agent_data:/data
    restart: unless-stopped

volumes:
  agent_data:
```

### Workflow deploy
1. `git push` lên GitHub
2. SSH vào GCP VM
3. `git pull && docker-compose up -d --build`

### GCP VM khuyến nghị
- Instance type: `e2-small` (2 vCPU, 2GB RAM) — đủ cho tải này
- OS: Ubuntu 22.04 LTS
- Disk: 20GB (SQLite + logs)

---

## 9. Dependencies chính

```
anthropic>=0.40.0
requests>=2.31.0
beautifulsoup4>=4.12.0
websocket-client>=1.7.0
APScheduler>=3.10.0
python-dotenv>=1.0.0
```

---

## 10. Những gì KHÔNG nằm trong scope v1

- Authentication/multi-user (chỉ 1 channel, 1 người dùng)
- Web UI dashboard
- Gửi email/báo cáo PDF formatted
- Lưu trữ file crawl dài hạn (chỉ giữ 30 ngày)
- Rate limiting / retry logic phức tạp
