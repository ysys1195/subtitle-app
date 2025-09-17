from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, Response, HTTPException
from pathlib import Path
import tempfile

from ..services.translate_to_jp import generate_translated_txt

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

@router.post("")
def translate_to_jp(file: UploadFile = File(...)):
    try:
        input_path, td = _save_upload_to_temp(file)
        out_path = input_path.parent / "translated_output.txt"  # 既存と同名
        generate_translated_txt(input_path, out_path)
        data = out_path.read_bytes()
        td.cleanup()
        return Response(
            content=data,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename=\"translated_output.txt\"'}
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
