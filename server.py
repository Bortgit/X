"""Servidor FastAPI: expone el webhook de Instagram y un endpoint de salud."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from channels.instagram import router as instagram_router
from core import blackstorie
from core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    blackstorie.ensure_blackstorie_files(settings)
    story = blackstorie.read_story(settings)
    if story.is_active:
        logging.info("JUGANDO: %s caracteres activos", story.char_count)
    else:
        logging.info("SIN JUEGO: blackstorie.txt vacio, el bot no respondera")
    yield


app = FastAPI(title="Blackstories Bot", lifespan=lifespan)
app.include_router(instagram_router)


@app.get("/health")
def health() -> dict:
    story = blackstorie.read_story(settings)
    return {
        "status": "ok",
        "jugando": story.is_active,
        "caracteres": story.char_count,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
