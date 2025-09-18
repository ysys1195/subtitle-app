from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool
from pathlib import Path
import tempfile
import logging
import time
import shutil
import asyncio
import os

from ..services.en_subs import generate_en_subtitled_video
# 日本語版を実装したら次を有効化
# from ..services.jp_subs import generate_jp_subtitled_video

router = APIRouter()
logger = logging.getLogger(__name__)

# 同時実行制御（Whisper/ffmpeg は重いので制限）
def _get_max_concurrency() -> int:
    val = os.getenv("MAX_CONCURRENCY", "1").strip()
    try:
        n = int(val)
        if n < 1:
            raise ValueError
        return n
    except Exception:
        logger.warning("MAX_CONCURRENCY is invalid: %r -> fallback to 1", val)
        return 1

_SEM = asyncio.Semaphore(_get_max_concurrency())

# ===== 入力バリデーション（拡張子/サイズ） =====
_ALLOWED_EXTS = {"mp4", "mov", "mkv", "webm", "m4v"}

def _get_max_upload_mb() -> int:
    val = os.getenv("MAX_UPLOAD_MB", "200").strip()
    try:
        n = int(val)
        if n < 1:
            raise ValueError
        return n
    except Exception:
        logger.warning("MAX_UPLOAD_MB is invalid: %r -> fallback to 200", val)
        return 200

def _is_extension_allowed(filename: str | None) -> bool:
    if not filename:
        return False
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext in _ALLOWED_EXTS

def _save_upload_to_temp(upload_file: UploadFile) -> tuple[Path, tempfile.TemporaryDirectory]:
    """
    UploadFile を一時ディレクトリに保存して (path, tmpdir) を返す。
    呼び出し側で tmpdir.cleanup() を必ず呼ぶこと。
    """
    td = tempfile.TemporaryDirectory()
    dst = Path(td.name) / (upload_file.filename or "input.mp4")
    with open(dst, "wb") as f:
        # 1MB チャンクでストリーミング保存
        shutil.copyfileobj(upload_file.file, f, length=1024 * 1024)
    return dst, td

@router.post("/en")
async def subtitles_en(request: Request, file: UploadFile = File(...)):
    start = time.perf_counter()
    try:
        filename = file.filename or "(no-name)"
        # 拡張子のホワイトリスト
        if not _is_extension_allowed(file.filename):
            raise HTTPException(status_code=422, detail="unsupported file extension")
        # 簡易入力バリデーション（動画以外は 422）。multipart は application/octet-stream になることがあるため許容。
        if file.content_type and not (
            file.content_type.startswith("video/") or file.content_type == "application/octet-stream"
        ):
            raise HTTPException(status_code=422, detail=f"unsupported content_type: {file.content_type}")
        # Content-Length による早期サイズチェック（存在する場合のみ）
        max_mb = _get_max_upload_mb()
        max_bytes = max_mb * 1024 * 1024
        cl = request.headers.get("content-length")
        if cl:
            try:
                content_length = int(cl)
                if content_length > max_bytes:
                    raise HTTPException(status_code=413, detail="payload too large")
            except ValueError:
                pass
        logger.info("/subtitles/en received: filename=%s max_upload_mb=%d", filename, max_mb)
        in_path, td = _save_upload_to_temp(file)
        # 実サイズの最終チェック（アップロード後のファイルサイズ）
        try:
            actual_size = in_path.stat().st_size
            if actual_size > max_bytes:
                raise HTTPException(status_code=413, detail="payload too large")
        except Exception:
            pass
        out_name = f"{Path(filename).stem}_subs.mp4"
        out_path = in_path.parent / out_name
        # Whisper 推論 + ffmpeg 実行はスレッドプールへ委譲（同時実行をセマフォで制御）
        acquire_start = time.perf_counter()
        async with _SEM:
            queued_ms = (time.perf_counter() - acquire_start) * 1000
            if queued_ms > 1:
                logger.info("/subtitles/en queued_ms=%.1f (concurrency limit)", queued_ms)
            await run_in_threadpool(generate_en_subtitled_video, in_path, out_path)

        size_bytes = out_path.stat().st_size
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            "/subtitles/en success: filename=%s elapsed_ms=%.1f size_bytes=%d",
            filename, elapsed, size_bytes,
        )
        return FileResponse(
            path=out_path,
            media_type="video/mp4",
            filename=out_name,
            background=BackgroundTask(td.cleanup),
        )
    except HTTPException:
        # すでに適切なステータスが付与されているケース（入力不備など）
        try:
            td.cleanup()  # type: ignore[name-defined]
        except Exception:
            pass
        raise
    except Exception as e:
        logger.exception("/subtitles/en failed: %s", e)
        try:
            # 失敗時は明示的に一時ディレクトリをクリーンアップ
            td.cleanup()  # type: ignore[name-defined]
        except Exception:
            pass
        # 内部エラーは 500 に丸める
        raise HTTPException(status_code=500, detail="internal error")