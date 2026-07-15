# HƯỚNG DẪN SỬ DỤNG TỪ A-Z (dành cho người chưa biết gì)

> Mục tiêu: một người chưa từng dùng Docker/Python làm theo từng bước là chạy được bot.
> Thời gian dự kiến: 30–45 phút lần đầu.

## Bot này làm gì?

Đây là một "trợ lý ảo" chạy trên chat nội bộ **netChat**. Nó tự động:
- Đọc tin công nghệ mạng lõi từ các trang 3GPP, GSMA, ETSI, Nokia... hàng tuần
- Viết báo cáo xu thế và gửi vào channel chat của nhóm
- Trả lời khi bạn nhắn tin riêng hoặc gọi `@tên_bot` trong nhóm
- Tóm tắt file PDF/Word khi bạn gửi file vào chat

## PHẦN 1 — Cài phần mềm cần thiết (làm 1 lần duy nhất)

### Bước 1.1. Cài Docker Desktop

Docker là phần mềm giúp chạy bot trong một "hộp" riêng biệt, không đụng gì đến máy bạn.

1. Tải tại: https://www.docker.com/products/docker-desktop/
2. Cài đặt → khởi động lại máy nếu được yêu cầu
3. Mở **Docker Desktop**, chờ góc dưới trái hiện màu xanh (engine running)

### Bước 1.2. Cài Git

Git dùng để tải mã nguồn về máy.

1. Tải tại: https://git-scm.com/download/win
2. Cài đặt với toàn bộ lựa chọn mặc định (bấm Next liên tục)

### Bước 1.3. Tải mã nguồn về máy

Mở **cmd** (phím Windows → gõ `cmd` → Enter), chạy lần lượt:

```cmd
cd /d D:\
git clone https://github.com/phantien02/baocaoxuthe_ML.git
cd baocaoxuthe_ML
```

## PHẦN 2 — Cấu hình (file .env)

Bot cần các "chìa khóa" để hoạt động. Tất cả nằm trong 1 file tên là `.env`.

### Bước 2.1. Tạo file .env

Trong thư mục dự án, copy file mẫu:

```cmd
copy .env.example .env
```

### Bước 2.2. Điền từng giá trị vào .env

Mở file `.env` bằng Notepad và điền:

| Dòng | Lấy ở đâu |
|---|---|
| `GEMINI_API_KEY=` | Vào https://aistudio.google.com/apikey → Create API key → copy chuỗi dán vào. Miễn phí. |
| `GEMINI_MODEL=` | Giữ nguyên như file mẫu |
| `NETCHAT_URL=` | Giữ nguyên `https://netchat.viettel.vn` |
| `NETCHAT_BOT_URL=` | Giữ nguyên `https://bot-netchat.viettel.vn` |
| `NETCHAT_TOKEN=` | Token của bot — xem chi tiết cách tạo trong `HUONG_DAN_CAI_DAT.md` (mục NETCHAT_TOKEN) |
| `NETCHAT_CHANNEL_NAME=` | Tên channel bot sẽ gửi báo cáo vào — nhìn URL trình duyệt khi mở channel: `https://netchat.viettel.vn/<team>/channels/<CHANNEL>`, lấy phần `<CHANNEL>`. Bot phải được mời vào channel này trước. |
| `REPORT_SCHEDULE_DAY=` | Ngày gửi báo cáo hàng tuần, ví dụ `mon` (thứ 2) |
| `REPORT_SCHEDULE_TIME=` | Giờ gửi, ví dụ `08:00` |
| `DB_PATH=` | Giữ nguyên `/data/agent.db` |

> ⚠️ **Tuyệt đối không gửi file .env cho ai / không đưa lên mạng** — trong đó có chìa khóa thật.

## PHẦN 3 — Chạy bot

Mở cmd tại thư mục dự án (hoặc dùng lại cửa sổ cũ), chạy:

```cmd
docker compose up -d --build
```

Lần đầu sẽ mất vài phút tải về. Khi hiện dòng `Started` là xong.

### Kiểm tra bot sống chưa

```cmd
docker logs baocaoxuthe-agent
```

Thấy 2 dòng này là bot đã chạy tốt:

```
Bot ready — listening on Netchat
Websocket connected
```

## PHẦN 4 — Sử dụng bot hàng ngày

Mở netChat và:

| Muốn gì | Làm gì |
|---|---|
| Xem bot biết làm gì | Nhắn riêng cho bot: `bạn làm được gì?` |
| Tạo báo cáo ngay | Gõ `!report` trong channel báo cáo hoặc DM |
| Xem trạng thái | Gõ `!status` |
| Tóm tắt tài liệu | Gửi file PDF/DOCX vào chat với bot |
| Xem lịch báo cáo tự động | Gõ `!schedule` hoặc `!lịch` |
| Hỏi trong nhóm | Gõ `@tên_bot` + câu hỏi (bot phải là thành viên nhóm) |
| Hỏi bất kỳ điều gì về mạng lõi | Nhắn riêng cho bot như chat với người |

Báo cáo tuần sẽ **tự động** được gửi vào channel theo lịch trong `.env` — không cần làm gì.

### Đổi lịch báo cáo (chỉ admin)

> ⚠️ Tính năng này chỉ dành cho **quản trị viên**. Tên quản trị viên phải được liệt kê trong biến `ADMIN_USERNAMES` trong file `.env` trên server.

Muốn đổi ngày/giờ gửi báo cáo mà **không cần khởi động lại bot**, dùng lệnh `!schedule`:

**Xem lịch hiện tại:**
```
!schedule
```
hoặc tên Việt:
```
!lịch
```

Kết quả sẽ hiển thị ngày + giờ báo cáo tự động chạy, ví dụ: `Báo cáo chạy: Thứ 2, 08:00 sáng. Lần kế tiếp: 17/07/2026 08:00.`

**Đổi lịch (chỉ admin):**
```
!schedule mon,fri 08:30
```

Ý nghĩa:
- `mon,fri` — gửi báo cáo vào **thứ 2 và thứ 6** (hoặc dùng số `1,5` → thứ 2 = 1, thứ 3 = 2, …, thứ 2 tuần sau = 0)
- `08:30` — lúc **08 giờ 30 phút** sáng

**Các định dạng ngày hợp lệ:**
- Tên tiếng Anh: `mon, tue, wed, thu, fri, sat, sun` (ngăn cách bằng dấu phẩy, không cần space)
- Số (0 = chủ nhật): `0, 1, 2, 3, 4, 5, 6` (0 = chủ nhật, 1 = thứ 2, …, 6 = thứ 7)
- Ví dụ khác:
  - `!schedule mon 09:00` → Mỗi thứ 2 09:00 sáng
  - `!schedule 2,4,6 14:30` → Mỗi thứ 3, 5, 7 14:30 chiều

**Lưu ý quan trọng:**
- Lịch sẽ lưu vào **cơ sở dữ liệu** — bot sẽ nhớ ngay cả khi khởi động lại.
- Chỉ **admin** (có tên trong `.env` biến `ADMIN_USERNAMES`) mới thay đổi được. Nếu gõ lệnh này mà bạn không phải admin, bot sẽ từ chối một cách lịch sự.
- Nếu bot báo cáo rằng chưa có admin nào cấu hình (`ADMIN_USERNAMES` trống), yêu cầu quản trị viên hệ thống thêm tên admin vào `.env` trên server rồi khởi động lại bot **một lần** để nạp biến cấu hình.

## PHẦN 5 — Các lệnh quản trị thường dùng

```cmd
:: Xem bot đang chạy không
docker ps

:: Xem log (100 dòng cuối)
docker logs --tail 100 baocaoxuthe-agent

:: Tắt bot
docker compose down

:: Bật lại bot
docker compose up -d

:: Cập nhật code mới nhất rồi chạy lại
git pull
docker compose up -d --build
```

## PHẦN 6 — Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `docker: command not found` | Docker Desktop chưa cài hoặc chưa mở. Mở Docker Desktop, chờ engine xanh. |
| Log báo `403` khi gửi tin | Kiểm tra `NETCHAT_BOT_URL` phải là `https://bot-netchat.viettel.vn`; token còn hạn không |
| Log báo `KeyError: 'NETCHAT_...'` | File `.env` thiếu dòng đó — mở `.env.example` so sánh và bổ sung |
| Bot không trả lời trong nhóm | Bot đã được mời vào nhóm chưa? Có gõ đúng `@tên_bot` không? |
| Báo cáo lỗi `503 UNAVAILABLE` | Gemini quá tải tạm thời — thử lại sau vài phút |
| Tiếng Việt hiển thị lỗi trong cmd | Chạy `chcp 65001` trước |

Vẫn tắc? Xem thêm `HUONG_DAN_TEST_API_NETCHAT.md` (test API bằng tay) hoặc hỏi người quản trị dự án.
