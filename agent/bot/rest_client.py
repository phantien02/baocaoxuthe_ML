import os
import requests


class NetchatRestClient:
    def __init__(self):
        self._base_url = os.environ["NETCHAT_URL"].rstrip("/")
        self._token = os.environ["NETCHAT_TOKEN"]
        self._team_name = os.environ["NETCHAT_TEAM_NAME"]
        self._channel_name = os.environ["NETCHAT_CHANNEL_NAME"]
        self._channel_id: str | None = None
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {self._token}"})

    def _api(self, method: str, path: str, **kwargs):
        url = f"{self._base_url}/api/v4{path}"
        resp = self._session.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def get_channel_id(self) -> str:
        if self._channel_id:
            return self._channel_id
        data = self._api("GET", f"/channels/name/{self._team_name}/{self._channel_name}")
        self._channel_id = data["id"]
        return self._channel_id

    def post_message(self, message: str, channel_id: str | None = None) -> dict:
        cid = channel_id or self.get_channel_id()
        return self._api("POST", "/posts", json={"channel_id": cid, "message": message})

    def download_file(self, file_id: str) -> bytes:
        url = f"{self._base_url}/api/v4/files/{file_id}"
        resp = self._session.get(url)
        resp.raise_for_status()
        return resp.content

    def get_file_info(self, file_id: str) -> dict:
        return self._api("GET", f"/files/{file_id}/info")
