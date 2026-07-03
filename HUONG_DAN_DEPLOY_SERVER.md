# HƯỚNG DẪN DEPLOY LÊN SERVER

> Áp dụng cho server Linux nội bộ. Thiết kế theo hướng: **một server chạy nhiều project Docker**,
> mỗi project độc lập, thêm/bớt project không ảnh hưởng nhau.

## 0. Điều kiện tiên quyết — KIỂM TRA TRƯỚC KHI LÀM GÌ KHÁC

Chạy từ server, xác nhận server "nhìn thấy" đủ 3 nhóm đích:

```bash
# 1. Netchat nội bộ (bắt buộc)
curl -s -o /dev/null -w "%{http_code}\n" https://netchat.viettel.vn
curl -s -o /dev/null -w "%{http_code}\n" https://bot-netchat.viettel.vn

# 2. Gemini API — cần internet (bắt buộc)
curl -s -o /dev/null -w "%{http_code}\n" https://generativelanguage.googleapis.com

# 3. Các nguồn crawl — cần internet (bắt buộc cho báo cáo tự động)
curl -s -o /dev/null -w "%{http_code}\n" https://www.3gpp.org
curl -s -o /dev/null -w "%{http_code}\n" https://www.gsma.com
curl -s -o /dev/null -w "%{http_code}\n" https://www.etsi.org
```

Nhóm 2 và 3 trả về mã khác 000 là thông. Nếu 000 (không kết nối được):
- Server ra internet qua **proxy** → xem mục 5.
- Server hoàn toàn không có internet → bot chỉ chạy được phần Netchat, không crawl/không gọi được Gemini — cần xin mở luồng.

## 1. Quy hoạch server cho nhiều project (làm 1 lần)

```
/opt/apps/
├── baocaoxuthe/          ← project này (git clone)
│   ├── docker-compose.yml
│   ├── .env              ← KHÔNG nằm trong git, copy tay
│   └── ...
├── project-2/            ← các project sau này, mỗi cái 1 thư mục
│   ├── docker-compose.yml
│   └── .env
└── ...
```

Nguyên tắc chung cho mọi project sau này:
- Mỗi project: **1 thư mục, 1 file compose, 1 file .env riêng**. Docker compose tự đặt tên
  container/volume/network theo thư mục → không đụng nhau.
- Dữ liệu luôn nằm trong **named volume** hoặc `./data/` của project — xóa container không mất data.
- Log luôn giới hạn dung lượng (`max-size`) — server chạy lâu không lo đầy đĩa.
- Project nào cần mở port thì ghi rõ trong compose và **không trùng port** giữa các project
  (bot này không cần mở port nào — chỉ gọi ra ngoài).

## 2. Cài Docker trên server (làm 1 lần)

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # logout/login lại để có hiệu lực
sudo systemctl enable --now docker

# Kiểm tra
docker --version && docker compose version
```

> RHEL/CentOS nội bộ không ra được get.docker.com: cài từ repo nội bộ hoặc RPM offline theo quy trình đơn vị.

## 3. Deploy lần đầu

```bash
# 3.1. Lấy code
sudo mkdir -p /opt/apps && sudo chown $USER /opt/apps
cd /opt/apps
git clone https://github.com/phantien02/baocaoxuthe_ML.git baocaoxuthe
cd baocaoxuthe

# 3.2. Copy .env từ máy cá nhân sang (KHÔNG commit .env lên git!)
# Chạy từ máy Windows cá nhân (Git Bash):
#   scp "D:\D-tienpc1\CODE_claudecode_agents\agent_baocaoxuthe\.env" user@<SERVER_IP>:/opt/apps/baocaoxuthe/.env

# 3.3. Build và chạy
docker compose up -d --build

# 3.4. Kiểm tra
docker logs -f baocaoxuthe-agent
# Phải thấy: "Bot ready — listening on Netchat" và "Websocket connected"
```

Test sâu hơn (gọi thật tới Netchat từ trong container):

```bash
docker exec baocaoxuthe-agent python -c "from agent.bot.rest_client import NetchatRestClient; c=NetchatRestClient(); print('bot id:', c.get_my_user_id()); print('channel:', c.get_channel_id())"
```

## 4. Mang dữ liệu cũ từ máy local sang (tùy chọn)

DB hiện tại (bài đã crawl tháng 6, các báo cáo đã tạo) nằm trong volume Docker ở máy local.
Muốn giữ:

```bash
# Máy local (PowerShell):
docker cp baocaoxuthe-agent:/data/agent.db D:\agent.db
scp D:\agent.db user@<SERVER_IP>:/tmp/agent.db

# Trên server:
docker compose stop
docker cp /tmp/agent.db baocaoxuthe-agent:/data/agent.db
docker compose start
```

Không mang thì bot bắt đầu DB trắng, crawl lại từ đầu — cũng không sao.

## 5. Server ra internet qua proxy (nếu có)

Hai chỗ cần khai proxy:

**a) Docker daemon** (để pull image từ Docker Hub) — `/etc/systemd/system/docker.service.d/proxy.conf`:

```ini
[Service]
Environment="HTTP_PROXY=http://proxy.noibo:3128"
Environment="HTTPS_PROXY=http://proxy.noibo:3128"
Environment="NO_PROXY=localhost,127.0.0.1"
```

```bash
sudo systemctl daemon-reload && sudo systemctl restart docker
```

**b) Container** (để bot gọi Gemini + crawl) — bỏ comment khối `environment:` trong
`docker-compose.yml` và điền proxy. **Quan trọng:** `NO_PROXY` phải chứa
`netchat.viettel.vn,bot-netchat.viettel.vn` — traffic nội bộ không được đi qua proxy.

## 6. Server không kéo được GitHub / Docker Hub

Build image ở máy local rồi chuyển file:

```powershell
# Máy local
docker compose build
docker save baocaoxuthe-agent:latest -o baocaoxuthe-agent.tar
scp baocaoxuthe-agent.tar user@<SERVER_IP>:/tmp/
scp -r . user@<SERVER_IP>:/opt/apps/baocaoxuthe/   # hoặc chỉ cần docker-compose.yml + .env
```

```bash
# Trên server
docker load -i /tmp/baocaoxuthe-agent.tar
cd /opt/apps/baocaoxuthe && docker compose up -d --no-build
```

## 7. Vận hành hàng ngày

```bash
docker ps                                  # trạng thái mọi project trên server
docker logs --tail 100 baocaoxuthe-agent   # xem log bot
docker compose restart                     # khởi động lại (trong thư mục project)

# Nâng cấp phiên bản mới
cd /opt/apps/baocaoxuthe
git pull
docker compose up -d --build               # DB giữ nguyên nhờ volume, migration tự chạy
```

Container có `restart: unless-stopped` — server reboot là bot tự dậy theo Docker.

## 8. Khác biệt local ↔ server cần nhớ

| Vấn đề | Local (máy trạm) | Server |
|---|---|---|
| Tên container | trước đây là `agent_baocaoxuthe-agent-1` (compose tự sinh), nay đã cố định thành `baocaoxuthe-agent` | `baocaoxuthe-agent` |
| WAF chặn User-Agent | Có (Trellix trên máy trạm) | Chưa rõ — UA `curl/8.4.0` đã là mặc định nên không cần làm gì; nếu server lại bị kiểu chặn khác thì đổi `NETCHAT_USER_AGENT` |
| Internet | Trực tiếp | Có thể qua proxy (mục 5) hoặc bị chặn (xin mở luồng) |
| Chạy 24/7 | Tắt máy là bot chết | Đúng mục đích — báo cáo tự động sáng thứ 2 chạy được |
