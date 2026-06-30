import json
import os
import threading
import websocket


class NetchatWebSocketClient:
    def __init__(self, on_post_callback):
        self._base_url = os.environ["NETCHAT_URL"].rstrip("/")
        self._token = os.environ["NETCHAT_TOKEN"]
        self._on_post_callback = on_post_callback
        self._ws: websocket.WebSocketApp | None = None
        self._thread: threading.Thread | None = None

    def _ws_url(self) -> str:
        return (
            self._base_url
            .replace("https://", "wss://")
            .replace("http://", "ws://")
            + "/api/v4/websocket"
        )

    def _on_open(self, ws):
        auth = {"seq": 1, "action": "authentication_challenge", "data": {"token": self._token}}
        ws.send(json.dumps(auth))
        print("[ws] connected")

    def _on_message(self, ws, raw):
        try:
            event = json.loads(raw)
            if event.get("event") == "posted":
                post = json.loads(event["data"]["post"])
                self._on_post_callback(post)
        except Exception as e:
            print(f"[ws] message error: {e}")

    def _on_error(self, ws, error):
        print(f"[ws] error: {error}")

    def _on_close(self, ws, code, msg):
        print(f"[ws] closed: {code}")

    def start(self):
        self._ws = websocket.WebSocketApp(
            self._ws_url(),
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._thread = threading.Thread(target=self._ws.run_forever, kwargs={"reconnect": 5}, daemon=True)
        self._thread.start()
        print("[ws] listener started")

    def stop(self):
        if self._ws:
            self._ws.close()
