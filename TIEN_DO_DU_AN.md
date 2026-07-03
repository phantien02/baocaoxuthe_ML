# TIẾN ĐỘ DỰ ÁN — Agent Báo cáo Xu thế Mạng lõi

> File này là "sổ theo dõi" của dự án: đã làm gì, đang ở đâu, tiếp theo làm gì.
> Cập nhật lần cuối: **03/07/2026**

## 1. Trạng thái hiện tại

| Hạng mục | Trạng thái |
|---|---|
| Môi trường chạy | ✅ **Server GCP** `35.247.154.93` — `/opt/apps/baocaoxuthe`, container `baocaoxuthe-agent` (deploy 03/07/2026) |
| Bot Netchat | ✅ Đang chạy 24/7 trên server, WebSocket ổn định, channel `ai_bot_clm_tienpc1` |
| Docker local (máy tienpc1) | ⏸️ Đã tắt (`docker compose down`) để tránh 2 bot trả lời trùng; volume DB tháng 6 vẫn còn trên máy local |
| Test tự động | ✅ 69/69 pass (`python -m pytest tests/`) |
| GitHub | https://github.com/phantien02/baocaoxuthe_ML (nhánh `master`) |

## 2. Chức năng đã hoàn thành

### Bot Netchat
- ✅ Gửi tin nhắn vào channel nhóm và DM (REST qua domain bot `bot-netchat.viettel.vn`)
- ✅ Nhận tin nhắn realtime qua WebSocket (domain `netchat.viettel.vn`)
- ✅ Lệnh: `!report`, `!status`, `!sources`, `!help`
- ✅ **Chat tự nhiên trong DM** — hỏi gì bot trả lời bằng Gemini (không cần lệnh)
- ✅ **Trả lời khi được @bot trong nhóm bất kỳ** (kể cả nhóm mới tạo, chỉ cần thêm bot vào)
- ✅ Nhận file PDF/DOCX đính kèm → tự đọc và tóm tắt
- ✅ Gửi tin kèm file (upload 2 bước, tối đa 5 file/post)
- ✅ Chống vòng lặp (bỏ qua tin của chính bot, tin hệ thống join/leave)

### Thu thập dữ liệu (crawler)
- ✅ 3GPP, GSMA, ETSI: đọc qua **RSS feed**, có ngày xuất bản thật (`published_at`)
- ✅ Nokia: crawl HTML (được bài nhưng không có ngày)
- ✅ Lưu SQLite kèm ngày xuất bản, chống trùng theo URL

### Báo cáo
- ✅ Báo cáo tuần tự động theo lịch (APScheduler, mặc định thứ 2 hàng tuần 08:00)
- ✅ Báo cáo thủ công qua lệnh `!report`
- ✅ Truy vấn theo khoảng ngày (`get_items_between`) → đã backfill 4 báo cáo tuần tháng 6/2026 vào channel (03/07/2026)

## 3. Các sửa đổi quan trọng gần đây (03/07/2026)

| Commit | Nội dung |
|---|---|
| `d398232` | Chuẩn hóa theo hướng dẫn API mới: REST đi qua `NETCHAT_BOT_URL`; thêm luồng DM 3 bước; gửi file 2 bước |
| `532dcb6` | Sửa lỗi WAF nội bộ chặn User-Agent `python-requests` → đặt UA `curl/8.4.0` (cấu hình qua `NETCHAT_USER_AGENT`) |
| `728daaa` | Chat tự nhiên DM + @mention; **sửa bug nhận diện DM** (channel_type nằm trong WebSocket event, không nằm trong post) |
| `4bc37ad` | Crawler chuyển sang RSS (3GPP/GSMA/ETSI); DB thêm cột `published_at` + migration; backfill báo cáo tháng 6 |

## 4. Hiện trạng nguồn dữ liệu (❗cần theo dõi)

| Nguồn | Trạng thái | Vấn đề / Ghi chú |
|---|---|---|
| 3GPP | ✅ Tốt | RSS, ~22 bài, có ngày |
| GSMA | ✅ Tốt | RSS, ~10 bài, có ngày |
| ETSI | ✅ Tốt | RSS, ~15 bài, có ngày |
| Nokia | ⚠️ Một phần | Crawl HTML được ~8 bài nhưng **không có ngày xuất bản** → bài rơi vào báo cáo theo ngày crawl |
| Ericsson | ❌ Hỏng | Server chặn bot mọi ngả (403, kể cả RSS, kể cả đổi User-Agent) — cần đổi URL nguồn khác (ví dụ trang press-release) hoặc bỏ |
| Huawei | ❌ Hỏng | Không tìm thấy RSS feed; trang HTML không trả về bài — cần tìm URL nguồn khác |

## 5. Việc tiếp theo cần làm (backlog)

1. **Sửa 3 nguồn hỏng/thiếu** (mục 4): tìm nguồn thay thế cho Ericsson/Huawei; tìm cách lấy ngày xuất bản cho Nokia (vào trang chi tiết từng bài hoặc tìm feed khác).
2. ~~Deploy server chính thức~~ ✅ Xong 03/07/2026 (GCP, xem `HUONG_DAN_DEPLOY_SERVER.md`). Còn lại: xác nhận crawler chạy tốt từ IP GCP (GSMA/ETSI trả 403 ở trang gốc khi curl — cần chạy thử crawl từ server), và cân nhắc chuyển DB tháng 6 từ máy local sang.
3. Cân nhắc lưu **lịch sử hội thoại** cho chat tự nhiên (hiện mỗi tin nhắn trả lời độc lập, bot không nhớ câu trước).
4. Retry/backoff khi Gemini 503 trong luồng chạy tự động (script backfill đã có, luồng scheduler chưa có).
5. Giới hạn độ dài tin nhắn gửi Netchat (báo cáo quá dài có thể vượt giới hạn ký tự 1 post).
6. Log ra file thay vì chỉ stdout container.

## 6. Cần test / kiểm chứng

- [x] DM chat tự nhiên (user test 03/07 — OK)
- [x] @bot trong nhóm cũ và nhóm mới (user test 03/07 — OK)
- [x] 4 báo cáo tuần tháng 6 gửi vào channel (03/07 — OK)
- [ ] Báo cáo tự động theo lịch chạy đúng vào thứ 2 08:00 (chờ đến lịch gần nhất)
- [ ] Gửi file PDF/DOCX cho bot để tóm tắt (chưa test với file thật sau đợt refactor)
- [ ] Bot tự phục hồi khi mất mạng/Netchat restart (WebSocket auto-reconnect)
- [ ] Migration DB trên volume cũ hoạt động đúng khi nâng cấp container

## 7. Quy ước cập nhật file này

Mỗi lần có thay đổi đáng kể (thêm chức năng, sửa lỗi lớn, deploy): thêm dòng vào mục 3,
cập nhật mục 1/4/5/6 tương ứng. Giữ ngắn gọn — chi tiết kỹ thuật để trong `LLD.md`.
