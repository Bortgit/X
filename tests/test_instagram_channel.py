from __future__ import annotations

import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from channels.instagram import extract_events, verify_signature, verify_webhook
from core.config import Settings


def _cfg(**overrides):
    base = dict(ig_verify_token="mi-token-secreto", ig_app_secret="")
    base.update(overrides)
    return Settings(**base)


def test_verify_webhook_token_correcto():
    cfg = _cfg()
    result = verify_webhook("subscribe", "mi-token-secreto", "reto123", cfg)
    assert result == "reto123"


def test_verify_webhook_token_incorrecto():
    cfg = _cfg()
    result = verify_webhook("subscribe", "token-malo", "reto123", cfg)
    assert result is None


def test_verify_webhook_modo_incorrecto():
    cfg = _cfg()
    result = verify_webhook("unsubscribe", "mi-token-secreto", "reto123", cfg)
    assert result is None


def test_verify_signature_correcta():
    secret = "app-secret-de-prueba"
    body = b'{"object": "instagram", "entry": []}'
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_signature(body, signature, secret) is True


def test_verify_signature_incorrecta():
    secret = "app-secret-de-prueba"
    body = b'{"object": "instagram", "entry": []}'
    signature = "sha256=" + hmac.new(b"otro-secreto", body, hashlib.sha256).hexdigest()
    assert verify_signature(body, signature, secret) is False


def test_verify_signature_cuerpo_manipulado():
    secret = "app-secret-de-prueba"
    body = b'{"object": "instagram", "entry": []}'
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    body_manipulado = b'{"object": "instagram", "entry": [1]}'
    assert verify_signature(body_manipulado, signature, secret) is False


def test_verify_signature_sin_cabecera():
    assert verify_signature(b"{}", None, "secreto") is False


def test_extract_events_mensaje_normal():
    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "page-id",
                "messaging": [
                    {
                        "sender": {"id": "user-123"},
                        "recipient": {"id": "page-id"},
                        "timestamp": 1234567890,
                        "message": {"mid": "mid-1", "text": "reto ¿es un asesinato?"},
                    }
                ],
            }
        ],
    }
    events = extract_events(payload)
    assert events == [
        {"sender_id": "user-123", "message_id": "mid-1", "text": "reto ¿es un asesinato?"}
    ]


def test_extract_events_ignora_eco_y_deliveries():
    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "page-id",
                "messaging": [
                    {"sender": {"id": "u1"}, "message": {"mid": "m1", "text": "eco", "is_echo": True}},
                    {"sender": {"id": "u1"}, "delivery": {"mids": ["m1"], "watermark": 1}},
                    {"sender": {"id": "u1"}, "read": {"watermark": 1}},
                ],
            }
        ],
    }
    assert extract_events(payload) == []


def test_webhook_get_verificacion_end_to_end(monkeypatch):
    import channels.instagram as ig_mod

    monkeypatch.setattr(ig_mod, "default_settings", _cfg(ig_verify_token="token-test"))
    from server import app

    client = TestClient(app)
    resp = client.get(
        "/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "token-test", "hub.challenge": "abc123"},
    )
    assert resp.status_code == 200
    assert resp.text == "abc123"


def test_webhook_get_verificacion_token_erroneo(monkeypatch):
    import channels.instagram as ig_mod

    monkeypatch.setattr(ig_mod, "default_settings", _cfg(ig_verify_token="token-test"))
    from server import app

    client = TestClient(app)
    resp = client.get(
        "/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "otro", "hub.challenge": "abc123"},
    )
    assert resp.status_code == 403


def test_webhook_post_sin_historia_activa_no_falla():
    from server import app

    client = TestClient(app)
    payload = {
        "object": "instagram",
        "entry": [
            {
                "id": "page-id",
                "messaging": [
                    {
                        "sender": {"id": "user-999"},
                        "message": {"mid": "mid-999", "text": "reto ¿hay juego?"},
                    }
                ],
            }
        ],
    }
    resp = client.post("/webhook", content=json.dumps(payload))
    assert resp.status_code == 200
