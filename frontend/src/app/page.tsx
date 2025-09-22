'use client';
import { useState } from 'react';
import { postEnglishSubtitles } from '../lib/api/postEnglishSubtitles';

export default function Page() {
  const [file, setFile] = useState<File | null>(null);
  const [downloading, setDownloading] = useState(false);

  const onSubmit = async () => {
    if (!file) return;
    setDownloading(true);
    try {
      const blob = await postEnglishSubtitles(file, {
        apiBase: process.env.NEXT_PUBLIC_API_BASE,
        timeoutMs: 30 * 60 * 1000, // 重処理のため長め
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'output_subs.mp4';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(e instanceof Error ? e.message : String(e));
    } finally {
      setDownloading(false);
    }
  };

  return (
    <main style={{ padding: 24 }}>
      <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      <button onClick={onSubmit} disabled={!file || downloading} style={{ marginLeft: 12 }}>
        {downloading ? '処理中...' : '送信'}
      </button>
    </main>
  );
}
