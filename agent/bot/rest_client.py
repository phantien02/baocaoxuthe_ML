import os
import requests

# Giới hạn của netChat: 1 post gắn tối đa 5 file
MAX_FILES_PER_POST = 5


class NetchatRestClient:
    def __init__(self):
        # Bot Token bắt buộc gọi REST qua domain bot (bot-netchat.viettel.vn).
        # Gọi nhầm sang domain người dùng sẽ bị 403 "API bot phải được gọi qua BMS".
        base = os.environ.get("NETCHAT_BOT_URL") or os.environ["NETCHAT_URL"]
        self._base_url = base.rstrip("/")
        self._token = os.environ["NETCHAT_TOKEN"]
        self._team_name = os.environ["NETCHAT_TEAM_NAME"]
        self._channel_name = os.environ["NETCHAT_CHANNEL_NAME"]
        # Đặt sẵn NETCHAT_CHANNEL_ID thì khỏi cần tra cứu
        self._channel_id: str | None = os.environ.get("NETCHAT_CHANNEL_ID") or None
        self._me: dict | None = None
        self._user_id_cache: dict[str, str] = {}
        self._session = requests.Session()
        # WAF nội bộ chặn theo User-Agent (python-requests/PowerShell/Postman bị 403
        # trang HTML; curl đi qua được) — xem mục 1.2 và mục 5 HUONG_DAN_TEST_API_NETCHAT.md
        user_agent = os.environ.get("NETCHAT_USER_AGENT", "curl/8.4.0")
        self._session.headers.update({
            "Authorization": f"Bearer {self._token}",
            "User-Agent": user_agent,
        })

    def _api(self, method: str, path: str, **kwargs):
        url = f"{self._base_url}/api/v4{path}"
        resp = self._session.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def get_channel_id(self) -> str:
        if self._channel_id:
            return self._channel_id
        # Gateway bot chặn /channels/name/{team}/{channel} (api.bot.endpoint_not_allowed);
        # /users/me/channels được phép nên liệt kê rồi lọc theo tên channel
        channels = self._api("GET", "/users/me/channels")
        for ch in channels:
            if ch.get("name") == self._channel_name:
                self._channel_id = ch["id"]
                return self._channel_id
        raise RuntimeError(
            f"Bot không phải thành viên channel '{self._channel_name}' — "
            "thêm bot vào channel hoặc đặt NETCHAT_CHANNEL_ID trong .env"
        )

    def get_me(self) -> dict:
        if self._me is None:
            self._me = self._api("GET", "/users/me")
        return self._me

    def get_my_user_id(self) -> str:
        return self.get_me()["id"]

    def get_my_username(self) -> str:
        return self.get_me()["username"]

    def get_user_id(self, username: str) -> str:
        # API chỉ nhận ID nội bộ 26 ký tự, không nhận username — luôn tra ID trước
        if username not in self._user_id_cache:
            data = self._api("GET", f"/users/username/{username}")
            self._user_id_cache[username] = data["id"]
        return self._user_id_cache[username]

    def create_direct_channel(self, user_id: str) -> str:
        # Idempotent: 2 user đã từng chat thì server trả về channel cũ
        data = self._api("POST", "/channels/direct", json=[self.get_my_user_id(), user_id])
        return data["id"]

    def send_direct_message(self, username: str, message: str, file_ids: list[str] | None = None) -> dict:
        channel_id = self.create_direct_channel(self.get_user_id(username))
        return self.post_message(message, channel_id, file_ids=file_ids)

    def post_message(self, message: str, channel_id: str | None = None,
                     file_ids: list[str] | None = None) -> dict:
        cid = channel_id or self.get_channel_id()
        body: dict = {"channel_id": cid, "message": message}
        if file_ids:
            if len(file_ids) > MAX_FILES_PER_POST:
                raise ValueError(f"Tối đa {MAX_FILES_PER_POST} file mỗi post")
            body["file_ids"] = list(file_ids)
        return self._api("POST", "/posts", json=body)

    def upload_file(self, file_path: str, channel_id: str | None = None) -> str:
        # Gửi file là quy trình 2 bước: upload multipart lấy file_id, rồi gắn vào post.
        # file_id chỉ gắn được vào đúng 1 post và phải cùng channel đã upload.
        cid = channel_id or self.get_channel_id()
        with open(file_path, "rb") as f:
            data = self._api(
                "POST", "/files",
                data={"channel_id": cid},
                files={"files": (os.path.basename(file_path), f)},
            )
        return data["file_infos"][0]["id"]

    def send_file(self, file_path: str, message: str = "", channel_id: str | None = None) -> dict:
        cid = channel_id or self.get_channel_id()
        file_id = self.upload_file(file_path, cid)
        return self.post_message(message, cid, file_ids=[file_id])

    def download_file(self, file_id: str) -> bytes:
        url = f"{self._base_url}/api/v4/files/{file_id}"
        resp = self._session.get(url)
        resp.raise_for_status()
        return resp.content

    def get_file_info(self, file_id: str) -> dict:
        return self._api("GET", f"/files/{file_id}/info")
