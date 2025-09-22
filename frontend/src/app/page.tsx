'use client';
import { useState, useRef } from 'react';
import { postEnglishSubtitles } from '../lib/api/postEnglishSubtitles';

export default function Page() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);

  const onSubmit = async () => {
    if (!file) return;
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
      alert(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main style={{ padding: 24 }}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
        <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
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
