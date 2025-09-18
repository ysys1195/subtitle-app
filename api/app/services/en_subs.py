from __future__ import annotations

import math
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional

from faster_whisper import WhisperModel
import logging

logger = logging.getLogger(__name__)

# ===== モデルのシングルトン読み込み =====
_MODEL: Optional[WhisperModel] = None

def _get_model() -> WhisperModel:
    """
    faster-whisper の WhisperModel をモジュール内で1度だけ初期化して使い回す。
    環境変数:
      WHISPER_MODEL : tiny/base/small/medium/large-v3 (default: small)
      DEVICE        : auto/cpu/cuda/metal (default: auto)
      COMPUTE_TYPE  : float32/float16/int8_float16/int8 (default: auto)
    """
    global _MODEL
    if _MODEL is None:
        model_name = os.getenv("WHISPER_MODEL", "small")
        device = os.getenv("DEVICE", "auto")
        compute_type_env = os.getenv("COMPUTE_TYPE", "").strip()  # e.g. "float16", "int8_float16", "int8"
        kwargs = {}
        if compute_type_env:
            kwargs["compute_type"] = compute_type_env  # only set when explicitly provided
        _MODEL = WhisperModel(
            model_size_or_path=model_name,
            device=device,
            **kwargs,
        )
        logger.info(
            "WhisperModel initialized: model=%s device=%s compute_type=%s",
            model_name,
            device,
            kwargs.get("compute_type", "auto"),
        )
    return _MODEL

# ===== 文字列整形（長文の自動改行） =====
def _wrap_text(text: str, max_chars: int = 40) -> str:
    words = text.strip().split()
    lines, cur, n = [], [], 0
    for w in words:
        add = len(w) + (1 if cur else 0)
        if n + add > max_chars:
            lines.append(" ".join(cur))
            cur, n = [w], len(w)
        else:
            cur.append(w)
            n += add
    if cur:
        lines.append(" ".join(cur))
    return "\n".join(lines) if lines else ""

# ===== タイムスタンプ（SRT形式） =====
def _srt_ts(t: float) -> str:
    if t < 0:
        t = 0.0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - math.floor(t)) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

# ===== SRTを書き出し =====
def _write_srt(segments: List[Tuple[float, float, str]], srt_path: Path) -> None:
    lines: List[str] = []
    idx = 1
    for start, end, text in segments:
        if not text.strip():
            continue
        lines.append(str(idx))
        lines.append(f"{_srt_ts(start)} --> {_srt_ts(end)}")
        lines.append(_wrap_text(text, max_chars=40))
        lines.append("")
        idx += 1
    srt_path.write_text("\n".join(lines), encoding="utf-8")

# ===== パスのエスケープ（ffmpeg subtitles= フィルタ用） =====
def _escape_for_subtitles_filter(p: Path) -> str:
    pp = p.resolve().as_posix()
    escaped = pp.replace("'", "\\'")
    return "filename='{}'".format(escaped)

# ===== ffmpeg エンコードパラメータ（環境変数） =====
def _get_ffmpeg_encode_params() -> List[str]:
    """
    環境変数から ffmpeg の画質/速度パラメータを取得する。
      - FFMPEG_CRF   : 0-51（低いほど高画質。デフォルト 23）
      - FFMPEG_PRESET: ultrafast~placebo（デフォルト medium）
    いずれも未設定/不正値の場合はデフォルトを使用する。
    """
    crf_env = os.getenv("FFMPEG_CRF", "23").strip()
    preset_env = os.getenv("FFMPEG_PRESET", "medium").strip()

    # CRF の簡易バリデーション（整数でない/範囲外は既定値にフォールバック）
    crf_value = "23"
    try:
        crf_int = int(crf_env)
        if 0 <= crf_int <= 51:
            crf_value = str(crf_int)
        else:
            logger.warning("FFMPEG_CRF out of range (0-51): %r -> fallback to 23", crf_env)
    except Exception:
        if crf_env:
            logger.warning("FFMPEG_CRF is not integer: %r -> fallback to 23", crf_env)

    preset_value = preset_env or "medium"

    logger.info("ffmpeg encode params: crf=%s preset=%s", crf_value, preset_value)
    return ["-crf", crf_value, "-preset", preset_value]

# ===== 字幕焼き込み（SRT + ffmpeg） =====
def _burn_srt_with_ffmpeg(video_path: Path, srt_path: Path, out_path: Path) -> None:
    """
    SRT を焼き込んで MP4 を出力する。
    - yuv420p / +faststart で QuickTime / Safari 互換向上
    - 音声が無い入力でも壊れないように -map 0:a? を使用
    """
    vf = f"subtitles={_escape_for_subtitles_filter(srt_path)}"
    encode_params = _get_ffmpeg_encode_params()
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", vf,
        "-map", "0:v:0",
        "-map", "0:a?",
        "-c:v", "libx264",
        *encode_params,
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",
        "-level", "4.0",
        "-c:a", "aac",
        "-movflags", "+faststart",
        "-shortest",
        str(out_path),
    ]
    logger.info("Running ffmpeg: %s", " ".join(cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        stderr = proc.stderr.decode(errors='ignore')
        logger.error("ffmpeg failed (code=%s): %s", proc.returncode, stderr)
        raise RuntimeError(f"ffmpeg failed ({proc.returncode}): {stderr}")
    logger.info("ffmpeg succeeded: output=%s", out_path)

# ===== 文字起こし → [(start, end, text), ...] =====
def _transcribe_segments(input_media: Path) -> List[Tuple[float, float, str]]:
    model = _get_model()
    segments, info = model.transcribe(
        str(input_media),
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=150),
        beam_size=5,
        language="en",
    )
    out: List[Tuple[float, float, str]] = []
    for seg in segments:
        text = (seg.text or "").strip()
        if text:
            out.append((float(seg.start), float(seg.end), text))
    return out

# ===== 公開関数：英語→英語字幕を焼いた動画を作る =====
def generate_en_subtitled_video(input_path: Path, out_path: Path) -> Path:
    if not input_path.exists():
        raise FileNotFoundError(f"input not found: {input_path}")

    segments = _transcribe_segments(input_path)
    with tempfile.TemporaryDirectory() as td:
        srt_path = Path(td) / "subs.srt"
        _write_srt(segments, srt_path)
        _burn_srt_with_ffmpeg(input_path, srt_path, out_path)
    return out_path
