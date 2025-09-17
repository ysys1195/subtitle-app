from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import subtitles  # ← translate は未実装なら読み込まない

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
