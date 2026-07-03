import json

import pytest
import responses as resp_lib
from agent.bot.rest_client import NetchatRestClient

# REST với Bot Token phải đi qua domain bot (NETCHAT_BOT_URL) — xem HUONG_DAN_TEST_API_NETCHAT.md
BOT = "https://bot-netchat.test.vn/api/v4"


# Gateway bot chỉ cho phép /users/me/channels — tra channel bằng cách lọc theo tên
MY_CHANNELS = [
    {"id": "dm1", "name": "botid__userid", "type": "D"},
    {"id": "chan123", "name": "test-channel", "type": "P"},
]


@resp_lib.activate
def test_get_channel_id():
    resp_lib.add(resp_lib.GET, f"{BOT}/users/me/channels", json=MY_CHANNELS, status=200)
    client = NetchatRestClient()
    cid = client.get_channel_id()
    assert cid == "chan123"


@resp_lib.activate
def test_get_channel_id_cached():
    resp_lib.add(resp_lib.GET, f"{BOT}/users/me/channels", json=MY_CHANNELS, status=200)
    client = NetchatRestClient()
    client.get_channel_id()
    client.get_channel_id()  # second call must not re-hit API
    assert len(resp_lib.calls) == 1


def test_get_channel_id_from_env(monkeypatch):
    monkeypatch.setenv("NETCHAT_CHANNEL_ID", "preset_chan")
    client = NetchatRestClient()
    assert client.get_channel_id() == "preset_chan"  # no API call needed


@resp_lib.activate
def test_get_channel_id_not_a_member():
    resp_lib.add(resp_lib.GET, f"{BOT}/users/me/channels", json=[], status=200)
    client = NetchatRestClient()
    with pytest.raises(RuntimeError):
        client.get_channel_id()


@resp_lib.activate
def test_rest_uses_bot_domain_not_user_domain():
    resp_lib.add(resp_lib.GET, f"{BOT}/users/me/channels", json=MY_CHANNELS, status=200)
    client = NetchatRestClient()
    client.get_channel_id()
    assert resp_lib.calls[0].request.url.startswith("https://bot-netchat.test.vn/")


@resp_lib.activate
def test_post_message():
    resp_lib.add(resp_lib.GET, f"{BOT}/users/me/channels", json=MY_CHANNELS, status=200)
    resp_lib.add(
        resp_lib.POST,
        f"{BOT}/posts",
        json={"id": "post456", "message": "Hello"},
        status=201,
    )
    client = NetchatRestClient()
    result = client.post_message("Hello")
    assert result["id"] == "post456"


@resp_lib.activate
def test_post_message_with_explicit_channel():
    resp_lib.add(
        resp_lib.POST,
        f"{BOT}/posts",
        json={"id": "post789"},
        status=201,
    )
    client = NetchatRestClient()
    client.post_message("Hello", channel_id="explicit_chan")
    body = resp_lib.calls[0].request.body
    assert "explicit_chan" in body.decode('utf-8')


@resp_lib.activate
def test_post_message_with_file_ids():
    resp_lib.add(
        resp_lib.POST,
        f"{BOT}/posts",
        json={"id": "post1"},
        status=201,
    )
    client = NetchatRestClient()
    client.post_message("Gui kem file", channel_id="chan123", file_ids=["file1", "file2"])
    body = json.loads(resp_lib.calls[0].request.body.decode("utf-8"))
    assert body["file_ids"] == ["file1", "file2"]


def test_post_message_rejects_more_than_5_files():
    client = NetchatRestClient()
    with pytest.raises(ValueError):
        client.post_message("qua nhieu", channel_id="chan123",
                            file_ids=["f1", "f2", "f3", "f4", "f5", "f6"])


@resp_lib.activate
def test_get_user_id():
    resp_lib.add(
        resp_lib.GET,
        f"{BOT}/users/username/tienpc1",
        json={"id": "6xin6bfe97dwxb3prsi5ii71yo", "username": "tienpc1"},
        status=200,
    )
    client = NetchatRestClient()
    assert client.get_user_id("tienpc1") == "6xin6bfe97dwxb3prsi5ii71yo"
    client.get_user_id("tienpc1")  # cached — no second call
    assert len(resp_lib.calls) == 1


@resp_lib.activate
def test_send_direct_message_full_flow():
    # Luồng DM 3 bước theo hướng dẫn: username -> user_id -> direct channel -> post
    resp_lib.add(resp_lib.GET, f"{BOT}/users/username/tienpc1",
                 json={"id": "user_target"}, status=200)
    resp_lib.add(resp_lib.GET, f"{BOT}/users/me",
                 json={"id": "user_bot"}, status=200)
    resp_lib.add(resp_lib.POST, f"{BOT}/channels/direct",
                 json={"id": "dm_chan", "type": "D"}, status=201)
    resp_lib.add(resp_lib.POST, f"{BOT}/posts",
                 json={"id": "post_dm"}, status=201)

    client = NetchatRestClient()
    result = client.send_direct_message("tienpc1", "Xin chao")
    assert result["id"] == "post_dm"

    direct_body = json.loads(resp_lib.calls[2].request.body.decode("utf-8"))
    assert sorted(direct_body) == ["user_bot", "user_target"]
    post_body = json.loads(resp_lib.calls[3].request.body.decode("utf-8"))
    assert post_body["channel_id"] == "dm_chan"


@resp_lib.activate
def test_upload_and_send_file(tmp_path):
    # Gửi file 2 bước: POST /files (multipart) lấy file_id -> POST /posts kèm file_ids
    f = tmp_path / "report.txt"
    f.write_text("noi dung bao cao")
    resp_lib.add(resp_lib.POST, f"{BOT}/files",
                 json={"file_infos": [{"id": "file_abc", "name": "report.txt"}]},
                 status=201)
    resp_lib.add(resp_lib.POST, f"{BOT}/posts",
                 json={"id": "post_file"}, status=201)

    client = NetchatRestClient()
    result = client.send_file(str(f), "Bao cao tuan", channel_id="chan123")
    assert result["id"] == "post_file"

    upload_req = resp_lib.calls[0].request
    assert "multipart/form-data" in upload_req.headers["Content-Type"]
    post_body = json.loads(resp_lib.calls[1].request.body.decode("utf-8"))
    assert post_body["file_ids"] == ["file_abc"]
    assert post_body["channel_id"] == "chan123"  # cùng channel với lúc upload


@resp_lib.activate
def test_add_reaction():
    resp_lib.add(resp_lib.GET, f"{BOT}/users/me",
                 json={"id": "user_bot"}, status=200)
    resp_lib.add(resp_lib.POST, f"{BOT}/reactions",
                 json={"user_id": "user_bot", "post_id": "post1", "emoji_name": "thumbsup"},
                 status=201)
    client = NetchatRestClient()
    client.add_reaction("post1")
    body = json.loads(resp_lib.calls[1].request.body.decode("utf-8"))
    assert body == {"user_id": "user_bot", "post_id": "post1", "emoji_name": "thumbsup"}


@resp_lib.activate
def test_download_file():
    resp_lib.add(
        resp_lib.GET,
        f"{BOT}/files/file123",
        body=b"PDF content bytes",
        status=200,
    )
    client = NetchatRestClient()
    data = client.download_file("file123")
    assert data == b"PDF content bytes"


@resp_lib.activate
def test_get_file_info():
    resp_lib.add(
        resp_lib.GET,
        f"{BOT}/files/file123/info",
        json={"id": "file123", "name": "spec.pdf", "extension": "pdf"},
        status=200,
    )
    client = NetchatRestClient()
    info = client.get_file_info("file123")
    assert info["name"] == "spec.pdf"
