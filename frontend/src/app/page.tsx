'use client';
import { useState, useRef } from 'react';
import { postEnglishSubtitles } from '../lib/api/postEnglishSubtitles';
import { ApiError } from '../lib/errors/ApiError';

export default function Page() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const MAX_UPLOAD_BYTES = 200 * 1024 * 1024; // 200MB（バックエンド既定値と同じ）
  const ALLOWED_EXTS = new Set(['mp4', 'mov', 'mkv', 'webm', 'm4v']);

  const onSubmit = async () => {
    if (!file) return;

    // 事前バリデーション（拡張子 / サイズ）
    const name = (file.name || '').toLowerCase();
    const ext = name.includes('.') ? name.split('.').pop() || '' : '';
    if (!ALLOWED_EXTS.has(ext)) {
      alert('対応していない拡張子です。mp4/mov/mkv/webm/m4v を選択してください。');
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      alert('ファイルが大きすぎます。200MB 以下の動画を選択してください。');
      return;
    }
    setLoading(true);
    try {
      const blob = await postEnglishSubtitles(file, {
        apiBase: process.env.NEXT_PUBLIC_API_BASE,
        timeoutMs: 30 * 60 * 1000, // 重処理のため長め
      });
      // 画面内再生のため、Object URL を生成して <video> に設定
      if (videoUrl) URL.revokeObjectURL(videoUrl);
      const url = URL.createObjectURL(blob);
      setVideoUrl(url);
      // 自動再生（ユーザー操作起点であれば多くのブラウザで許可）
      requestAnimationFrame(() => {
        videoRef.current?.play().catch(() => {});
      });
    } catch (e) {
      if (e instanceof ApiError) {
        if (e.status === 413) {
          alert(
            'アップロードが失敗しました（413: ファイルが大きすぎます）。200MB 以下の動画を選択してください。',
          );
        } else if (e.status === 422) {
          alert(
            'アップロードが失敗しました（422: 入力が不正です）。対応拡張子・動画ファイルかをご確認ください。',
          );
        } else if (e.status === 500) {
          alert('サーバ内部エラー（500）が発生しました。時間を置いて再試行してください。');
        } else {
          alert(`エラーが発生しました（HTTP ${e.status}）: ${e.detail || e.message}`);
        }
      } else if (e instanceof DOMException && e.name === 'AbortError') {
        alert('処理が中断されました。');
      } else if (e instanceof Error) {
        alert(e.message);
      } else {
        alert(String(e));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <main style={{ padding: 24 }}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
        <input
          type="file"
          accept="video/*"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <button onClick={onSubmit} disabled={!file || loading}>
          {loading ? '処理中...' : '字幕付き動画を生成'}
        </button>
      </div>
      {videoUrl && (
        <video
          ref={videoRef}
          src={videoUrl}
          controls
          style={{ width: '100%', maxWidth: 720, background: '#000' }}
        />
      )}
    </main>
  );
}
