# agent_baocaoxuthe

Agent tự động crawl tin tức công nghệ mạng Core Network và tạo báo cáo xu thế hàng tuần, giao tiếp qua Netchat (Mattermost-compatible).

## Tính năng

- Crawl tự động từ 6 nguồn: 3GPP, GSMA, ETSI, Ericsson, Nokia, Huawei
- Tạo báo cáo song ngữ (VI tổng quan + EN kỹ thuật) dùng Claude AI
- Nhận lệnh qua Netchat: `!report`, `!status`, `!sources`, `!help`
- Tóm tắt tài liệu PDF/DOCX đính kèm
- Lịch báo cáo tự động hàng tuần (APScheduler)
- Lưu trữ SQLite, deploy Docker trên GCP VM

## Yêu cầu

- Docker + Docker Compose
- Claude API key (Anthropic)
- Netchat bot token (`mm_xxx` format)

## Cài đặt

```bash
cp .env.example .env
# Điền các biến môi trường trong .env
docker-compose up -d
```

## Biến môi trường

| Biến | Mô tả | Ví dụ |
|------|-------|-------|
| `CLAUDE_API_KEY` | Anthropic API key | `sk-ant-...` |
| `CLAUDE_MODEL` | Claude model ID | `claude-sonnet-4-6` |
| `NETCHAT_URL` | URL Netchat server | `https://netchat.viettel.vn` |
| `NETCHAT_TOKEN` | Bot token | `mm_xxx...` |
| `NETCHAT_TEAM_NAME` | Tên team | `kttc` |
| `NETCHAT_CHANNEL_NAME` | Tên channel | `core-network-report` |
| `REPORT_SCHEDULE_DAY` | Ngày trong tuần (0=Thứ 2) | `0` |
| `REPORT_SCHEDULE_TIME` | Giờ chạy (HH:MM) | `08:00` |
| `REPORT_TIMEZONE` | Múi giờ | `Asia/Ho_Chi_Minh` |
| `DB_PATH` | Đường dẫn SQLite DB | `/data/agent.db` |

## Lệnh bot

| Lệnh | Chức năng |
|------|-----------|
| `!report` | Tạo báo cáo từ 7 ngày qua |
| `!status` | Thời gian crawl cuối + lịch tiếp theo |
| `!sources` | Danh sách nguồn đang theo dõi |
| `!help` | Trợ giúp |
| _(đính kèm PDF/DOCX)_ | Tóm tắt tài liệu |

## Deploy lên GCP VM

### 1. Tạo VM

```bash
gcloud compute instances create agent-baocaoxuthe \
  --machine-type=e2-micro \
  --zone=asia-southeast1-b \
  --image-family=debian-12 \
  --image-project=debian-cloud \
  --boot-disk-size=20GB
```

### 2. Cài Docker trên VM

```bash
# SSH vào VM
gcloud compute ssh agent-baocaoxuthe --zone=asia-southeast1-b

# Cài Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### 3. Deploy agent

```bash
# Trên máy local — build và push image
docker build -t gcr.io/YOUR_PROJECT/agent_baocaoxuthe:latest .
docker push gcr.io/YOUR_PROJECT/agent_baocaoxuthe:latest

# Trên VM — pull và chạy
docker pull gcr.io/YOUR_PROJECT/agent_baocaoxuthe:latest
docker run -d \
  --name agent_baocaoxuthe \
  --restart unless-stopped \
  --env-file /home/$USER/agent.env \
  -v agent_data:/data \
  gcr.io/YOUR_PROJECT/agent_baocaoxuthe:latest
```

### 4. Dùng docker-compose (khuyến nghị)

```bash
# Copy docker-compose.yml và .env lên VM
scp docker-compose.yml .env agent-baocaoxuthe:/home/$USER/

# SSH vào VM và chạy
docker-compose up -d
docker-compose logs -f
```

## Kiểm tra

```bash
# Xem log
docker-compose logs -f

# Chạy tests
pytest tests/ -v

# Kiểm tra DB
sqlite3 /data/agent.db ".tables"
sqlite3 /data/agent.db "SELECT COUNT(*) FROM crawled_items;"
```

## Cấu trúc dự án

```
agent_baocaoxuthe/
├── agent/
│   ├── bot/
│   │   ├── commands.py       # Xử lý lệnh bot
│   │   ├── rest_client.py    # Netchat REST API
│   │   └── websocket_client.py # Netchat WebSocket
│   ├── crawler/
│   │   ├── base.py           # BaseCrawler
│   │   ├── source_3gpp.py    # 3GPP crawler
│   │   ├── source_gsma.py    # GSMA crawler
│   │   ├── source_etsi.py    # ETSI crawler
│   │   ├── source_ericsson.py # Ericsson crawler
│   │   ├── source_nokia.py   # Nokia crawler
│   │   └── source_huawei.py  # Huawei crawler
│   ├── llm/
│   │   ├── claude_client.py  # Claude API client
│   │   └── prompts.py        # Bilingual prompts
│   ├── scheduler/
│   │   └── __init__.py       # APScheduler weekly cron
│   ├── storage/
│   │   └── database.py       # SQLite storage
│   └── main.py               # Entry point
├── tests/                    # 50 tests
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```
