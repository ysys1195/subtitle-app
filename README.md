## subtitle-bff

英語音声の動画から英語字幕を生成し、ffmpeg で焼き込んだ MP4 を返す FastAPI サービス。

### 概要

- エンドポイント: `POST /subtitles/en`（`multipart/form-data` の `file` に動画を添付）
- Whisper 実装: faster-whisper（環境変数未設定でデフォルト使用。必要に応じて変更可）
- 出力仕様: H.264（yuv420p, High Profile, +faststart）

## 前提

- Python 3.13
- ffmpeg/ffprobe がインストール済み
  ```bash
  ffmpeg -version
  ffprobe -version
  ```

## セットアップ

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip freeze --exclude-editable > requirements-lock.txt
```

## 環境変数（設定不要・デフォルト使用）

このプロジェクトは環境変数を設定しなくても動作します。未設定時は以下のデフォルトが使用されます。

- `WHISPER_MODEL`: small
- `DEVICE`: auto
- `COMPUTE_TYPE`: 自動判定（未指定のため）

## サーバ起動

```bash
uvicorn api.app.main:app --host 0.0.0.0 --port 8000 --log-level info
```

- 動作確認用 UI: `http://localhost:8000/docs`
- ヘルスチェック: `http://localhost:8000/healthz`

## サンプル動画の用意

- リポジトリルートに `input.mp4` がある場合はそのまま利用できます。

## 動作確認（完了条件）

1. API を叩いて MP4 を取得
   ```bash
   curl -sS -X POST -F file=@input.mp4 http://localhost:8000/subtitles/en -o result.mp4
   test -s result.mp4
   ```
2. 映像のコーデック/ピクセルフォーマット/プロファイルの確認
   ```bash
   ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,pix_fmt,profile -of default=nk=1:nw=1 result.mp4
   # 期待出力（順不同）:
   # h264
   # yuv420p
   # High
   ```
3. `+faststart`（moov が先頭）確認
   ```bash
   # moov と mdat の出現順を確認（moov の行番号 < mdat の行番号なら OK）
   grep -a -n -m1 -E 'moov|mdat' result.mp4
   ```

## ログ

- 本アプリは dictConfig で統一フォーマットに設定済み:
  `%(asctime)s %(levelname)s %(name)s: %(message)s`
- 主な出力
  - FastAPI/uvicorn の INFO ログ
  - `api.app.services.en_subs`:
    - Whisper 初期化情報（model/device/compute_type）
    - ffmpeg 実行コマンド概要、成功/失敗（失敗時は stderr も ERROR で出力）
  - `api.app.routes.subtitles`:
    - リクエスト受信/完了（ファイル名、処理時間、出力サイズ）

## 依存固定の運用

- 人手編集: `requirements.txt`
- 機械生成: `requirements-lock.txt`

  ```bash
  # 依存更新後にロックファイルを再生成
  pip freeze --exclude-editable > requirements-lock.txt

  # 別環境ではロックからインストール（再現性重視）
  pip install -r requirements-lock.txt
  ```

## トラブルシュート

- ffmpeg が見つからない/失敗する
  - `ffmpeg -version` で確認。失敗時はサーバログに stderr が出力されます。
- 推論が遅い/失敗する
  - モデルを小さく（`WHISPER_MODEL=tiny` など）、Apple Silicon は`DEVICE=metal`, `COMPUTE_TYPE=float16` を推奨。
- CORS でブロックされる
  - 開発中は全許可設定。必要に応じて `main.py` の `allow_origins` を調整してください。
