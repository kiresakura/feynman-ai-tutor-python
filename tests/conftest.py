import socket

import pytest
import requests


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """測試一律不准連網：任何 socket 連線都直接失敗。"""

    def blocked(*args, **kwargs):
        raise RuntimeError("Network access is disabled in tests")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


@pytest.fixture(autouse=True)
def _no_env_key(monkeypatch):
    """預設沒有 GEMINI_API_KEY；設成空字串，本機 .env 也不會被 load_dotenv 帶進測試。"""
    monkeypatch.setenv("GEMINI_API_KEY", "")


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeGemini:
    """取代 requests.post 的假 Gemini：記錄每次請求，回傳預先設定的內容。"""

    def __init__(self):
        self.calls = []
        self.status_code = 200
        self.payload = None

    def reply(self, text):
        self.status_code = 200
        self.payload = {"candidates": [{"content": {"parts": [{"text": text}]}}]}

    def __call__(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return FakeResponse(self.status_code, self.payload)


@pytest.fixture
def gemini(monkeypatch):
    fake = FakeGemini()
    monkeypatch.setattr(requests, "post", fake)
    return fake
