from __future__ import annotations
from pathlib import Path

def generate_jp_subtitled_video(input_path: Path, out_path: Path) -> Path:
    """
    TODO: 英語→英語文字起こし (faster-whisper) → 日本語翻訳 → SRT生成 → ffmpegで焼き込み
    en_subs.py をベースに、出力テキストを翻訳してから SRT を書き出す実装にする。
    """
    ...
    return out_path