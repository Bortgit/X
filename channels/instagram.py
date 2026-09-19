"""Adaptador de canal para Instagram (Meta Messaging API).

No hace ninguna llamada real por si mismo salvo `send_message`, que solo
se invoca cuando `handle_message` devuelve una respuesta. Sin
credenciales configuradas, `send_message` simplemente registra en el log
lo que habria enviado (ver README para lo que falta verificar contra la
documentacion oficial de Meta).
"""
from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import APIRouter, Header, Query, Request, Response

from core.config import Settings, settings as default_settings
from core.engine import handle_message

logger = logging.getLogger("blackstories.channels.instagram")

router = APIRouter()


def verify_webhook(mode: str | None, token: str | None, challenge: str | None, cfg: Settings) -> str | None:
    """Verificacion GET del webhook (hub.challenge). Devuelve el challenge si es valido."""
    if mode == "subscribe" and token == cfg.ig_verify_token and cfg.ig_verify_token:
        return challenge
    return None


def verify_signature(raw_body: bytes, signature_header: str | None, app_secret: str) -> bool:
    """Valida la cabecera X-Hub-Signature-256 (HMAC SHA256 sobre el cuerpo crudo)."""
    if not signature_header or not app_secret:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    received = signature_header.split("=", 1)[1]
    return hmac.compare_digest(expected, received)


def extract_events(payload: dict) -> list[dict]:
    """Extrae {sender_id, message_id, text} de un payload de webhook de Meta."""
    events: list[dict] = []
    for entry in payload.get("entry", []):
        for messaging_event in entry.get("messaging", []):
            message = messaging_event.get("message")
            if not message:
                continue  # ignora deliveries, reads, postbacks, etc.
            if message.get("is_echo"):
                continue  # ignora eco de mensajes enviados por el propio bot
            sender_id = messaging_event.get("sender", {}).get("id")
            message_id = message.get("mid")
            text = message.get("text")
            if not sender_id or text is None:
                continue
            events.append({"sender_id": sender_id, "message_id": message_id, "text": text})
    return events


def send_message(recipient_id: str, text: str, cfg: Settings) -> bool:
    """Envia la respuesta por la API de mensajeria de Meta. Devuelve True si se envio."""
    if not cfg.ig_page_access_token:
        logger.warning(
            "IG_PAGE_ACCESS_TOKEN no configurado; no se envia nada (simulado): a %s -> %r",
            recipient_id,
            text,
        )
        return False

    import httpx

    url = f"https://graph.facebook.com/{cfg.ig_graph_api_version}/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "messaging_type": "RESPONSE",
        "message": {"text": text},
    }
    try:
        resp = httpx.post(
            url,
            params={"access_token": cfg.ig_page_access_token},
            json=payload,
            timeout=cfg.model_timeout_seconds,
        )
        resp.raise_for_status()
        return True
    except httpx.HTTPError as exc:  # pragma: no cover - requiere credenciales reales
        logger.error("Error enviando mensaje a Instagram: %s", exc)
        return False


@router.get("/webhook")
def webhook_verify(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> Response:
    challenge = verify_webhook(hub_mode, hub_verify_token, hub_challenge, default_settings)
    if challenge is not None:
        return Response(content=challenge, media_type="text/plain", status_code=200)
    return Response(status_code=403)


@router.post("/webhook")
async def webhook_receive(request: Request, x_hub_signature_256: str | None = Header(default=None)) -> Response:
    raw_body = await request.body()

    if default_settings.ig_app_secret:
        if not verify_signature(raw_body, x_hub_signature_256, default_settings.ig_app_secret):
            logger.warning("Firma X-Hub-Signature-256 invalida; peticion rechazada")
            return Response(status_code=403)

    payload = await request.json()
    for event in extract_events(payload):
        response = handle_message(event["sender_id"], event["message_id"], event["text"])
        if response is not None:
            send_message(event["sender_id"], response, default_settings)

    return Response(status_code=200)
