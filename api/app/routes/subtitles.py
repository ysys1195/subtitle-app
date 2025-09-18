from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool
from pathlib import Path
import tempfile
import logging
import time
import shutil

from ..services.en_subs import generate_en_subtitled_video
# 日本語版を実装したら次を有効化
# from ..services.jp_subs import generate_jp_subtitled_video

router = APIRouter()
logger = logging.getLogger(__name__)

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
async def subtitles_en(file: UploadFile = File(...)):
    start = time.perf_counter()
    try:
        filename = file.filename or "(no-name)"
        # 簡易入力バリデーション（動画以外は 422）。multipart は application/octet-stream になることがあるため許容。
        if file.content_type and not (
            file.content_type.startswith("video/") or file.content_type == "application/octet-stream"
        ):
            raise HTTPException(status_code=422, detail=f"unsupported content_type: {file.content_type}")
        logger.info("/subtitles/en received: filename=%s size=?", filename)
        in_path, td = _save_upload_to_temp(file)
        out_name = f"{Path(filename).stem}_subs.mp4"
        out_path = in_path.parent / out_name
        # Whisper 推論 + ffmpeg 実行はスレッドプールへ委譲
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