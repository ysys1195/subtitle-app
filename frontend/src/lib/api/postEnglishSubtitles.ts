import { ApiError } from '../errors/ApiError';

/**
 * 英語字幕を焼き込んだMP4を生成するエンドポイントへ動画を送信するための薄いユーティリティ
 * 成功時はvideo/mp4のBlobを返す。失敗時はサーバからのdetailを含むApiErrorを投げる
 */
export type PostEnSubtitlesOptions = {
  /** API ベース URL（例: process.env.NEXT_PUBLIC_API_BASE） */
  apiBase?: string;
  /** Blob を送る際の仮ファイル名。File の場合は File.name を優先 */
  filename?: string;
  /** 外部からの中断指示（ユーザー操作など） */
  signal?: AbortSignal;
  /** タイムアウト（ms）。指定時は AbortController で中断 */
  timeoutMs?: number;
};

/**
 * 動画をmultipart/form-dataで POST {apiBase}/subtitles/enに送信し、MP4のBlobを受け取る
 * @param file - 送信する動画（File または Blob）
 * @param options - API ベース URL、ファイル名、キャンセルシグナル、タイムアウト等
 * @returns 成功時に `video/mp4` の Blob
 * @throws ApiError - HTTP エラー時にステータスと detail を保持して投げる
 * @throws DOMException('AbortError') - 中断時
 */
export async function postEnglishSubtitles(
  file: File | Blob,
  options?: PostEnSubtitlesOptions,
): Promise<Blob> {
  const apiBase = options?.apiBase ?? process.env.NEXT_PUBLIC_API_BASE ?? '';
  // API ベース URL は必須
  if (!apiBase) throw new Error('API base URL is not configured');

  const abortController = new AbortController();
  const timers: Array<ReturnType<typeof setTimeout>> = [];

  if (options?.signal) {
    // 既に中断済みなら即時中断、未中断なら一度だけ伝播
    if (options.signal.aborted) abortController.abort();
    else options.signal.addEventListener('abort', () => abortController.abort(), { once: true });
  }

  if (typeof options?.timeoutMs === 'number' && options.timeoutMs > 0) {
    // 指定ミリ秒後に自動で中断
    const t = setTimeout(() => abortController.abort(), options.timeoutMs);
    timers.push(t);
  }

  try {
    const form = new FormData();
    const filename = file instanceof File ? file.name : (options?.filename ?? 'input.mp4');
    form.append('file', file, filename);
    const endpoint = new URL('/subtitles/en', apiBase).toString();
    // 成功時はvideo/mp4、エラー時はapplication/jsonを優先
    const res = await fetch(endpoint, {
      method: 'POST',
      body: form,
      signal: abortController.signal,
      headers: {
        Accept: 'video/mp4,application/json;q=0.9,*/*;q=0.8',
      },
    });

    const contentType = (res.headers.get('Content-Type') || '').toLowerCase();
    // 成功かつvideo/mp4のときのみBlobを返す
    if (res.ok && contentType.startsWith('video/mp4')) {
      return await res.blob();
    }

    // エラー本文をContent-Typeに応じて抽出（JSON優先、なければtext）
    let detail = `HTTP ${res.status}`;
    try {
      if (contentType.includes('application/json')) {
        const data = await res.json();
        if (data && typeof data.detail === 'string') detail = data.detail;
        else detail = JSON.stringify(data);
      } else {
        detail = await res.text();
      }
    } catch {
      // エラーを握り潰し、フォールバックdetailを維持
    }
    throw new ApiError(res.status, detail);
  } catch (err) {
    // 中断はそのまま再送出し、呼び出し側で特別扱いさせる
    if (err instanceof DOMException && err.name === 'AbortError') throw err;
    throw err;
  } finally {
    // タイマー後始末
    timers.forEach(clearTimeout);
  }
}
