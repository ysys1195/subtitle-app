import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { postEnglishSubtitles } from '../postEnglishSubtitles';
import { ApiError } from '../../errors/ApiError';

describe('postEnglishSubtitles', () => {
  const API_BASE = 'http://example.com';

  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('200 + video/mp4の場合にBlobを返す', async () => {
    const mockFetch = vi.fn(async () => {
      const body = new Blob(['mp4data'], { type: 'video/mp4' });
      return new Response(body, {
        status: 200,
        headers: { 'Content-Type': 'video/mp4' },
      });
    });
    vi.stubGlobal('fetch', mockFetch);

    const input = new Blob(['dummy'], { type: 'video/mp4' });
    const blob = await postEnglishSubtitles(input, {
      apiBase: API_BASE,
      filename: 'input.mp4',
    });

    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toBe('video/mp4');
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, init] = mockFetch.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe(`${API_BASE}/subtitles/en`);
    expect(init?.method).toBe('POST');
    expect(init?.headers).toMatchObject({
      Accept: expect.stringContaining('video/mp4'),
    });
    expect(init?.body).toBeInstanceOf(FormData);
  });

  it('422(JSON)の場合にApiError(422, detail)を投げる', async () => {
    const mockFetch = vi.fn(async () => {
      return new Response(JSON.stringify({ detail: 'unsupported file extension' }), {
        status: 422,
        headers: { 'Content-Type': 'application/json' },
      });
    });
    vi.stubGlobal('fetch', mockFetch);

    const input = new Blob(['dummy'], { type: 'application/octet-stream' });
    try {
      await postEnglishSubtitles(input, { apiBase: API_BASE, filename: 'input.bin' });
      throw new Error('should not reach');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const err = e as ApiError;
      expect(err.status).toBe(422);
      expect(err.detail).toBe('unsupported file extension');
      expect(err.message).toBe('unsupported file extension');
    }
  });

  it('500(text)の場合にApiError(500, text)を投げる', async () => {
    const mockFetch = vi.fn(async () => {
      return new Response('internal error', {
        status: 500,
        headers: { 'Content-Type': 'text/plain' },
      });
    });
    vi.stubGlobal('fetch', mockFetch);

    const input = new Blob(['dummy'], { type: 'video/mp4' });
    try {
      await postEnglishSubtitles(input, { apiBase: API_BASE });
      throw new Error('should not reach');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const err = e as ApiError;
      expect(err.status).toBe(500);
      expect(err.detail).toBe('internal error');
      expect(err.message).toBe('internal error');
    }
  });

  it('413(JSON)の場合にApiError(413, detail)を投げる', async () => {
    const mockFetch = vi.fn(async () => {
      return new Response(JSON.stringify({ detail: 'payload too large' }), {
        status: 413,
        headers: { 'Content-Type': 'application/json' },
      });
    });
    vi.stubGlobal('fetch', mockFetch);

    const input = new Blob(['dummy'], { type: 'video/mp4' });
    try {
      await postEnglishSubtitles(input, { apiBase: API_BASE });
      throw new Error('should not reach');
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      const err = e as ApiError;
      expect(err.status).toBe(413);
      expect(err.detail).toBe('payload too large');
      expect(err.message).toBe('payload too large');
    }
  });

  it('timeoutMsによりAbortErrorを再送出する', async () => {
    const mockFetch = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      return new Promise<Response>((_resolve, reject) => {
        const signal = init?.signal as AbortSignal | undefined;
        const onAbort = () => {
          reject(new DOMException('Aborted', 'AbortError'));
        };
        if (signal) {
          if (signal.aborted) onAbort();
          else signal.addEventListener('abort', onAbort, { once: true });
        }
        // 決して解決しない（中断されるまで待機）
      });
    });
    vi.stubGlobal('fetch', mockFetch as unknown as typeof fetch);

    const input = new Blob(['dummy'], { type: 'video/mp4' });
    await expect(
      postEnglishSubtitles(input, { apiBase: API_BASE, timeoutMs: 5 }),
    ).rejects.toMatchObject({ name: 'AbortError' });
  });
});
