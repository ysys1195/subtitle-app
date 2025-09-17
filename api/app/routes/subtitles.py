from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, Response, HTTPException
from pathlib import Path
import tempfile
import logging
import time

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
        f.write(upload_file.file.read())
    return dst, td

@router.post("/en")
async def subtitles_en(file: UploadFile = File(...)):
    start = time.perf_counter()
    try:
        filename = file.filename or "(no-name)"
        logger.info("/subtitles/en received: filename=%s size=?", filename)
        in_path, td = _save_upload_to_temp(file)
        out_path = in_path.parent / "output_with_subs.mp4"
        generate_en_subtitled_video(in_path, out_path)

        data = out_path.read_bytes()
        td.cleanup()
        elapsed = (time.perf_counter() - start) * 1000
        logger.info("/subtitles/en success: filename=%s elapsed_ms=%.1f size_bytes=%d", filename, elapsed, len(data))
        return Response(
            content=data,
            media_type="video/mp4",
            headers={"Content-Disposition": 'attachment; filename="output_with_subs.mp4"'}
        )
    except Exception as e:
        logger.exception("/subtitles/en failed: %s", e)
        raise HTTPException(status_code=422, detail=str(e))