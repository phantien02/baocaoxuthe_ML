import pytest
import responses as resp_lib
from agent.bot.rest_client import NetchatRestClient


@resp_lib.activate
def test_get_channel_id():
    resp_lib.add(
        resp_lib.GET,
        "https://netchat.test.vn/api/v4/channels/name/test-team/test-channel",
        json={"id": "chan123", "name": "test-channel"},
        status=200,
    )
    client = NetchatRestClient()
    cid = client.get_channel_id()
    assert cid == "chan123"


@resp_lib.activate
def test_get_channel_id_cached():
    resp_lib.add(
        resp_lib.GET,
        "https://netchat.test.vn/api/v4/channels/name/test-team/test-channel",
        json={"id": "chan123"},
        status=200,
    )
    client = NetchatRestClient()
    client.get_channel_id()
    client.get_channel_id()  # second call must not re-hit API
    assert len(resp_lib.calls) == 1


@resp_lib.activate
def test_post_message():
    resp_lib.add(
        resp_lib.GET,
        "https://netchat.test.vn/api/v4/channels/name/test-team/test-channel",
        json={"id": "chan123"},
        status=200,
    )
    resp_lib.add(
        resp_lib.POST,
        "https://netchat.test.vn/api/v4/posts",
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
        "https://netchat.test.vn/api/v4/posts",
        json={"id": "post789"},
        status=201,
    )
    client = NetchatRestClient()
    client.post_message("Hello", channel_id="explicit_chan")
    body = resp_lib.calls[0].request.body
    assert "explicit_chan" in body.decode('utf-8')


@resp_lib.activate
def test_download_file():
    resp_lib.add(
        resp_lib.GET,
        "https://netchat.test.vn/api/v4/files/file123",
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
        "https://netchat.test.vn/api/v4/files/file123/info",
        json={"id": "file123", "name": "spec.pdf", "extension": "pdf"},
        status=200,
    )
    client = NetchatRestClient()
    info = client.get_file_info("file123")
    assert info["name"] == "spec.pdf"
