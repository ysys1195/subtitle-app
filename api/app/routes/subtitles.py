from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, Response, HTTPException
from pathlib import Path
import tempfile

from ..services.en_subs import generate_en_subtitled_video
# 日本語版を実装したら次を有効化
# from ..services.jp_subs import generate_jp_subtitled_video

router = APIRouter()

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
    try:
        in_path, td = _save_upload_to_temp(file)
        out_path = in_path.parent / "output_with_subs.mp4"
        generate_en_subtitled_video(in_path, out_path)

        data = out_path.read_bytes()
        td.cleanup()
        return Response(
            content=data,
            media_type="video/mp4",
            headers={"Content-Disposition": 'attachment; filename="output_with_subs.mp4"'}
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))