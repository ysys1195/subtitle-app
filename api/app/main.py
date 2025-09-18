from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import subtitles  # ← translate は未実装なら読み込まない
import logging
import logging.config

# ログ設定（標準出力へ統一フォーマットで出力）
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s %(name)s: %(message)s"
        }
    },
    "handlers": {
        "default": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        }
    },
    "loggers": {
        "uvicorn.error": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "fastapi": {"handlers": ["default"], "level": "INFO", "propagate": False},
        # アプリ配下（例: api.app...）
        "api": {"handlers": ["default"], "level": "INFO", "propagate": False},
    },
    "root": {"handlers": ["default"], "level": "INFO"},
}

logging.config.dictConfig(LOGGING_CONFIG)

app = FastAPI(title="subtitle-bff", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発中は緩めでOK
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(subtitles.router, prefix="/subtitles", tags=["subtitles"])

@app.get("/healthz")
def healthz():
    return {"ok": True}
