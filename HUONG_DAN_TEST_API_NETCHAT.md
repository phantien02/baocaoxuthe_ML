# HƯỚNG DẪN TEST API NETCHAT BẰNG CURL

> Quy trình từng bước theo thứ tự logic — đã kiểm chứng thực tế trên máy nội bộ Viettel.

## 1. Chuẩn bị trước khi test

### 1.1. Thông tin cần có

| Thông tin | Giá trị / Cách lấy |
|---|---|
| Server URL (Bot Token) | `https://bot-netchat.viettel.vn` |
| Server URL (token người dùng) | `https://netchat.viettel.vn` |
| Bot Token | Tạo trong netChat Admin Console (dạng chuỗi 26 ký tự) |
| channel_id, user_id, team_id | Lấy qua API — xem mục 3 (đây chính là lý do phải test theo thứ tự) |

> **QUAN TRỌNG:** Bot Token bắt buộc phải gọi qua domain `bot-netchat.viettel.vn`. Nếu gọi nhầm sang `netchat.viettel.vn` sẽ bị lỗi 403: *"API bot phải được gọi qua BMS kèm header xác minh hợp lệ"*.

### 1.2. Chọn công cụ chạy lệnh (rất quan trọng)

Trên máy nội bộ có cài phần mềm bảo mật (Viettel Endpoint Security / Trellix), một số ứng dụng bị chặn kết nối tới API. Kết quả kiểm chứng thực tế:

| Công cụ | Kết quả | Ghi chú |
|---|---|---|
| Command Prompt (cmd.exe) | ✔ Dùng được | Cú pháp nối dòng: dấu `^` |
| Git Bash | ✔ Dùng được | Cú pháp nối dòng: dấu `\` , hỗ trợ UTF-8 sẵn |
| PowerShell | ✘ Bị chặn | Trả về 400 Bad Request (nginx) dù lệnh đúng |
| Postman | ✘ Bị chặn | Trả về 400 Bad Request (nginx) dù request đúng |

**Khuyến nghị:** dùng **cmd.exe** (mở bằng: phím Windows → gõ "cmd" → Enter). Toàn bộ lệnh trong tài liệu này viết theo cú pháp cmd.exe.

**Lưu ý tiếng Việt có dấu:** trước khi gửi tin nhắn có dấu, chạy lệnh `chcp 65001` một lần sau khi mở cmd để bật UTF-8, nếu không chữ có dấu sẽ bị lỗi (ví dụ "gửi" thành "g?i").

### 1.3. Cấu trúc chung của mọi lệnh

Mọi request REST tới netChat đều gồm 4 thành phần:

```cmd
curl -X <METHOD> "<URL>" ^
  -H "Authorization: Bearer <TOKEN>" ^
  -H "Content-Type: application/json" ^
  -d "<JSON_BODY>"
```

- `-X` (`--request`): HTTP method — GET (đọc), POST (tạo), PUT (sửa), DELETE (xoá)
- `-H` (`--header`): header của request — luôn cần Authorization; thêm Content-Type khi có body JSON
- `-d` (`--data`): body dữ liệu gửi kèm (chỉ dùng với POST/PUT)
- Trong cmd.exe: nối dòng bằng `^`, JSON phải bọc bằng nháy kép và escape thành `\"` (không dùng nháy đơn như Bash)

## 2. Nguyên tắc cốt lõi: API chỉ nhận ID, không nhận tên

Hầu hết API của netChat (nền Mattermost) làm việc bằng **ID nội bộ** (chuỗi 26 ký tự, ví dụ `6xin6bfe97dwxb3prsi5ii71yo`) — **không nhận username hay tên hiển thị**. Nếu truyền username vào chỗ cần user_id sẽ bị lỗi 400 *"Không hợp lệ hoặc thiếu user_id"*.

Vì vậy thứ tự test luôn là: tra ID trước, dùng ID sau. Sơ đồ luồng đầy đủ để gửi tin nhắn trực tiếp (DM) chỉ từ username:

```
username
   |
   |  Bước 1: GET /api/v4/users/username/{username}
   v
user_id  (của người nhận + của bot)
   |
   |  Bước 2: POST /api/v4/channels/direct  body: [user_id_bot, user_id_nguoi_nhan]
   v
channel_id  (kênh DM giữa bot và người nhận)
   |
   |  Bước 3: POST /api/v4/posts  body: {channel_id, message}
   v
Tin nhắn được gửi
```

> **Ghi nhớ:** response của API này chính là input của API tiếp theo. Đây là pattern chuẩn của REST API.

## 3. Quy trình test từng bước (theo thứ tự logic)

### Bước 1 — Tra user_id từ username

Endpoint: `GET /api/v4/users/username/{username}`

```cmd
curl -X GET "https://bot-netchat.viettel.vn/api/v4/users/username/tienpc1" ^
  -H "Authorization: Bearer <TOKEN>"
```

Response (rút gọn) — lấy giá trị field `id`:

```json
{"id": "6xin6bfe97dwxb3prsi5ii71yo", "username": "tienpc1", ...}
```

Làm tương tự để lấy user_id của chính con bot (ví dụ username `bot_test_tienpc1`) — vì DM là cuộc trò chuyện giữa 2 user nên cần cả 2 ID.

### Bước 2 — Lấy/tạo channel_id của cuộc DM

Endpoint: `POST /api/v4/channels/direct` — Payload là mảng JSON gồm đúng 2 user_id.

```cmd
curl -X POST "https://bot-netchat.viettel.vn/api/v4/channels/direct" ^
  -H "Authorization: Bearer <TOKEN>" ^
  -H "Content-Type: application/json" ^
  -d "[\"<USER_ID_BOT>\",\"<USER_ID_NGUOI_NHAN>\"]"
```

Response (rút gọn) — lấy field `id`, đó chính là channel_id:

```json
{"id": "sar7somhzfrxxcr941nosrphqa", "type": "D", ...}
```

> **Lưu ý hay:** API này an toàn khi gọi lại nhiều lần — nếu 2 user đã từng chat, nó trả về channel cũ; nếu chưa, nó tạo mới. Không bao giờ tạo trùng.

### Bước 3 — Gửi tin nhắn vào channel_id

Endpoint: `POST /api/v4/posts`

```cmd
curl -X POST "https://bot-netchat.viettel.vn/api/v4/posts" ^
  -H "Authorization: Bearer <TOKEN>" ^
  -H "Content-Type: application/json" ^
  -d "{\"channel_id\":\"<CHANNEL_ID>\",\"message\":\"Xin chao\"}"
```

Response thành công trả về 201 Created kèm JSON của tin nhắn vừa tạo:

```json
{"id": "<POST_ID>", "channel_id": "<CHANNEL_ID>", "message": "Xin chao", "user_id": "<USER_ID_BOT>", ...}
```

**Gửi vào channel nhóm:** dùng y hệt lệnh trên, chỉ thay channel_id bằng ID của channel nhóm (lấy qua API mục 4.1).

## 4. Các API khác (sau khi đã có ID)

### 4.1. Lấy channel_id của channel nhóm

> **Lưu ý thực tế (kiểm chứng 07/2026):** gateway bot CHẶN endpoint tra channel theo tên
> (`/channels/name/...` trả về `api.bot.endpoint_not_allowed`). Cách hoạt động được là
> liệt kê các channel bot là thành viên rồi tìm theo trường `name`:

```cmd
curl -X GET "https://bot-netchat.viettel.vn/api/v4/users/me/channels" ^
  -H "Authorization: Bearer <TOKEN>"
```

Response là mảng JSON các channel (DM lẫn nhóm). Tìm phần tử có `name` trùng tên channel
cần gửi, lấy trường `id` — đó là channel_id. Điều kiện: **bot phải được thêm vào channel trước**
(mời bot vào channel như mời một thành viên bình thường).

### 4.2. Gửi tin nhắn kèm file (quy trình 2 bước)

File và tin nhắn là **2 resource khác nhau** trong REST, nên gửi file luôn gồm 2 request tách biệt: upload file lên server trước để lấy `file_id`, sau đó tạo tin nhắn có tham chiếu tới file_id đó. File upload xong mà chưa gắn vào post thì chưa ai nhìn thấy.

```
File trên máy
   |
   |  Bước 1: POST /api/v4/files   (multipart/form-data)
   |          -> server lưu file, trả về file_id
   v
file_id
   |
   |  Bước 2: POST /api/v4/posts   (application/json)
   |          body: {channel_id, message, file_ids: [file_id]}
   v
Tin nhắn kèm file xuất hiện trong channel
```

#### Vì sao Bước 1 dùng multipart/form-data, không dùng JSON?

`Content-Type` là lời khai báo "body tôi gửi lên có định dạng gì" để server biết cách đọc. Hai định dạng khác nhau ở chỗ:

- `application/json`: body là text thuần có cấu trúc JSON — phù hợp cho dữ liệu chữ/số. Nhưng file (ảnh, PDF...) là dữ liệu nhị phân (binary), nhét vào JSON phải encode base64, phình to ~33%.
- `multipart/form-data`: body chia thành nhiều "phần" (part) ngăn cách bằng chuỗi ranh giới (boundary) — mỗi phần có thể là text hoặc binary nguyên gốc. Nhờ vậy 1 request gửi được đồng thời field text (`channel_id`) và nội dung file binary.

**Trong curl:** dùng cờ `-F` thay cho `-d`. Cờ `-F` tự động đặt `Content-Type: multipart/form-data` kèm boundary — **không cần và không nên tự khai header này bằng tay** (tự khai mà thiếu boundary sẽ lỗi). Dấu `@` trước đường dẫn nghĩa là "đọc nội dung từ file này".

#### Bước 1 — Upload file lên server

```cmd
curl -X POST "https://bot-netchat.viettel.vn/api/v4/files" ^
  -H "Authorization: Bearer <TOKEN>" ^
  -F "channel_id=<CHANNEL_ID>" ^
  -F "files=@C:\duong\dan\toi\anh.png"
```

Response (rút gọn) — lấy giá trị `file_infos[0].id`:

```json
{"file_infos":[{"id":"<FILE_ID>","name":"anh.png","extension":"png",
  "size":491689,"mime_type":"image/png","width":992,"height":764,
  "has_preview_image":true,"mini_preview":"..."}],"client_ids":[]}
```

Server tự làm giúp một số việc khi upload:

- Tự nhận diện `mime_type` và đọc kích thước ảnh (width/height)
- Tự sinh `mini_preview` (thumbnail base64 siêu nhỏ) để app hiển thị mờ trong lúc chờ tải ảnh gốc
- Lúc này file ở trạng thái "chờ" — response chưa có `post_id` vì file chưa gắn với tin nhắn nào

#### Bước 2 — Tạo tin nhắn gắn file

Quay lại JSON bình thường, thêm mảng `file_ids` vào body của POST /posts:

```cmd
curl -X POST "https://bot-netchat.viettel.vn/api/v4/posts" ^
  -H "Authorization: Bearer <TOKEN>" ^
  -H "Content-Type: application/json" ^
  -d "{\"channel_id\":\"<CHANNEL_ID>\",\"message\":\"Gui kem file\",\"file_ids\":[\"<FILE_ID>\"]}"
```

Response thành công: trong `metadata.files` đã xuất hiện `post_id` — file chính thức được gắn vào tin nhắn và hiển thị trong channel.

#### Quy chế / giới hạn cần nhớ

- **1 file_id chỉ gắn được vào 1 post duy nhất** — muốn gửi lại cùng file lần nữa phải upload lại để lấy file_id mới.
- 1 post gắn được **tối đa 5 file** — mảng `file_ids` chứa nhiều ID cùng lúc: `["id1","id2",...]`
- channel_id khi upload (Bước 1) và khi post (Bước 2) phải **cùng một channel**.
- Upload nhiều file trong 1 request: lặp lại cờ `-F "files=@..."` nhiều lần — response trả về nhiều phần tử trong file_infos.

## 5. Bảng lỗi thường gặp và cách xử lý

| Lỗi | Nguyên nhân | Cách xử lý |
|---|---|---|
| 400 Bad Request (trang HTML nginx, không phải JSON) | Chạy lệnh từ PowerShell hoặc Postman — bị phần mềm bảo mật nội bộ chặn ở tầng WAF | Chuyển sang cmd.exe hoặc Git Bash. Đổi mạng KHÔNG giải quyết được. |
| 403 trang HTML (không phải JSON) khi gọi từ code Python | WAF chặn theo User-Agent (`python-requests` bị chặn giống PowerShell/Postman) | Đặt header `User-Agent` khác, ví dụ `curl/8.4.0` (code bot đã làm sẵn) |
| 403 JSON `api.bot.endpoint_not_allowed` | Bot Token chỉ được phép gọi một số endpoint nhất định (whitelist) | Dùng endpoint thay thế trong whitelist — ví dụ tra channel bằng `/users/me/channels` (mục 4.1) |
| 403 "API bot phải được gọi qua BMS..." | Dùng Bot Token nhưng gọi nhầm domain netchat.viettel.vn | Đổi sang `https://bot-netchat.viettel.vn` |
| 400 "Không hợp lệ hoặc thiếu user_id" | Truyền username (vd: tienpc1) vào chỗ cần user_id dạng ID 26 ký tự | Tra ID trước bằng `GET /users/username/{username}` (Bước 1) |
| 401 session_expired / TokenRequired | Lệnh nhiều dòng bị tách rời — chạy cú pháp Bash (dấu `\`) trong cmd, hoặc ngược lại | cmd dùng `^`, Git Bash dùng `\`. Không trộn lẫn. |
| `'-H' is not recognized as a command` | Dán lệnh cú pháp Bash vào cmd.exe — mỗi dòng bị hiểu là lệnh riêng | Dùng đúng bản lệnh có dấu `^` cho cmd |
| Tiếng Việt bị lỗi dấu ("g?i") | cmd.exe không mặc định UTF-8 | Chạy `chcp 65001` trước khi gửi tin có dấu |

## 6. Ghi chú bảo mật

- **Không dán token vào chat/email/tài liệu chia sẻ rộng.** Token bị lộ phải revoke ngay trong netChat Admin Console và tạo token mới.
- Token trong tài liệu này để dạng `<TOKEN>` — người dùng tự thay bằng token của mình khi chạy.
- Khi đưa vào code chatbot thật, lưu token trong biến môi trường / file `.env`, không hard-code trong source.

## 7. Tài liệu tham khảo

- Tài liệu gốc: `huong_dan_tich_hop_chatbot_netchat.docx` (cùng thư mục)
- REST API đầy đủ (netChat nền Mattermost): https://api.mattermost.com
- WebSocket events: https://api.mattermost.com/#tag/WebSocket
