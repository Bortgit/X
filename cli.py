#!/usr/bin/env python3
"""Canal de terminal para jugar y probar el bot sin Instagram.

Uso:
    python cli.py status
    python cli.py play [--user-id ID]
    python cli.py send "reto ¿es un asesinato?" [--user-id ID] [--message-id ID]
"""
from __future__ import annotations

import argparse
import logging
import sys
import uuid

from core import blackstorie, db
from core.config import settings
from core.engine import handle_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def cmd_status(_args: argparse.Namespace) -> None:
    story = blackstorie.read_story(settings)
    print(f"Archivo de historia: {settings.blackstorie_file}")
    if story.is_active:
        print(f"JUGANDO: {story.char_count} caracteres (hash {story.story_hash[:12]}...)")
    else:
        print("SIN JUEGO: blackstorie.txt vacio, el bot no respondera.")


def cmd_play(args: argparse.Namespace) -> None:
    user_id = args.user_id or f"cli-{uuid.uuid4().hex[:8]}"
    print(f"Jugando como usuario '{user_id}'. Escribe mensajes que empiecen por 'reto'.")
    print("Escribe 'salir' para terminar.\n")
    conn = db.get_connection(settings)
    try:
        while True:
            try:
                text = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if text.lower() in ("salir", "exit", "quit"):
                break
            if not text:
                continue
            message_id = uuid.uuid4().hex
            response = handle_message(user_id, message_id, text, conn=conn)
            if response is None:
                print("(el bot no ha respondido)")
            else:
                print(response)
    finally:
        conn.close()


def cmd_send(args: argparse.Namespace) -> None:
    user_id = args.user_id or "cli-user"
    message_id = args.message_id or uuid.uuid4().hex
    conn = db.get_connection(settings)
    try:
        response = handle_message(user_id, message_id, args.text, conn=conn)
    finally:
        conn.close()
    if response is None:
        print("(sin respuesta)")
    else:
        print(response)


def main(argv: list[str] | None = None) -> int:
    blackstorie.ensure_blackstorie_files(settings)

    parser = argparse.ArgumentParser(description="Bot de Black Stories - canal de terminal")
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="Muestra si hay historia activa")
    p_status.set_defaults(func=cmd_status)

    p_play = sub.add_parser("play", help="Juega de forma interactiva")
    p_play.add_argument("--user-id", default=None)
    p_play.set_defaults(func=cmd_play)

    p_send = sub.add_parser("send", help="Envia un unico mensaje y muestra la respuesta")
    p_send.add_argument("text")
    p_send.add_argument("--user-id", default=None)
    p_send.add_argument("--message-id", default=None)
    p_send.set_defaults(func=cmd_send)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
