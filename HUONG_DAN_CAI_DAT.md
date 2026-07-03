# Hướng dẫn cài đặt và cấu hình

## Bước 1: Tạo file .env

```powershell
cd D:\D-tienpc1\CODE_claudecode_agents\agent_baocaoxuthe
Copy-Item .env.example .env
notepad .env
```

---

## Bước 2: Điền các biến môi trường

### GEMINI_API_KEY
- Vào: https://aistudio.google.com/apikey
- Nhấn **Create API key**
- Copy key dạng `AIza...`
- Miễn phí, không cần thẻ ngân hàng

### GEMINI_MODEL
- Giữ nguyên: `gemini-2.0-flash` (miễn phí, đủ dùng)

---

### NETCHAT_URL
- Giữ nguyên: `https://netchat.viettel.vn` (domain người dùng — dùng cho WebSocket)

### NETCHAT_BOT_URL
- Giữ nguyên: `https://bot-netchat.viettel.vn`
- Đây là domain BẮT BUỘC cho REST API khi dùng Bot Token. Nếu gọi nhầm qua
  `netchat.viettel.vn` sẽ bị lỗi 403 *"API bot phải được gọi qua BMS kèm header
  xác minh hợp lệ"* (xem `HUONG_DAN_TEST_API_NETCHAT.md`)

### NETCHAT_TOKEN
- Mở Netchat trên trình duyệt
- Nhấn vào **Avatar (ảnh đại diện)** góc trái dưới → **Account Settings**
- Chọn tab **Security**
- Kéo xuống phần **Personal Access Tokens** → nhấn **Create**
- Đặt tên bất kỳ (ví dụ: `bot-baocao`) → **Save**
- Copy token dạng `mm_xxxxxxxxxxxxx...`

### NETCHAT_TEAM_NAME và NETCHAT_CHANNEL_NAME
Mở Netchat trên **trình duyệt**, vào đúng channel muốn bot post báo cáo vào.
Nhìn URL trên thanh địa chỉ:

```
https://netchat.viettel.vn/kttc-core/channels/core-network-report
                             ─────────         ────────────────────
                          TEAM_NAME              CHANNEL_NAME
```

- **TEAM_NAME** = phần ngay sau `netchat.viettel.vn/`
- **CHANNEL_NAME** = phần sau `/channels/`

> Lưu ý: đây là slug trong URL, **không phải tên hiển thị** trên giao diện.
> Ví dụ tên hiển thị "KTTC Core Network" nhưng slug URL có thể là `kttc-core`.

**Gợi ý:** Tạo một channel mới riêng cho bot (ví dụ `core-network-report`) để báo cáo không lẫn với chat thường.

---

### REPORT_SCHEDULE_DAY
Ngày trong tuần bot tự động gửi báo cáo:

| Giá trị | Ngày |
|---------|------|
| `mon`   | Thứ Hai |
| `tue`   | Thứ Ba |
| `wed`   | Thứ Tư |
| `thu`   | Thứ Năm |
| `fri`   | Thứ Sáu |
| `sat`   | Thứ Bảy |
| `sun`   | Chủ Nhật |

### REPORT_SCHEDULE_TIME
Giờ gửi báo cáo, định dạng `HH:MM`. Ví dụ: `08:00`

### REPORT_TIMEZONE
Giữ nguyên: `Asia/Ho_Chi_Minh`

### DB_PATH
Giữ nguyên: `/data/agent.db` (Docker tự quản lý)

---

## Bước 3: Chạy Docker

```powershell
docker compose up --build
```

Lần đầu mất 2-3 phút (tải Python base image). Khi thấy log:
```
[ws] connected
[ws] listener started
```
→ Bot đã online. Vào Netchat gõ `!help` trong channel để kiểm tra.

### Chạy nền (sau khi đã test xong):
```powershell
docker compose up --build -d
docker compose logs -f    # xem log real-time
docker compose down       # tắt bot
```

---

## Các lệnh bot

| Lệnh | Chức năng |
|------|-----------|
| `!report` | Tạo báo cáo ngay từ tin tức 7 ngày qua |
| `!status` | Xem thời gian crawl cuối + lịch báo cáo tiếp theo |
| `!sources` | Danh sách 6 nguồn đang theo dõi |
| `!help` | Hiện danh sách lệnh |
| _(đính kèm file PDF/DOCX)_ | Bot tóm tắt tài liệu bằng Gemini AI |

Bot cũng nhận lệnh qua **Direct Message (DM)** — gõ bất kỳ gì trong DM với bot là nó sẽ tạo báo cáo.
