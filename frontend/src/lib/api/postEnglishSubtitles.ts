export type PostEnSubtitlesOptions = {
  apiBase?: string;
  filename?: string;
  signal?: AbortSignal;
  timeoutMs?: number;
};

export async function postEnglishSubtitles(
  _file: File | Blob,
  _options?: PostEnSubtitlesOptions,
): Promise<Blob> {
  void _file;
  void _options;
  throw new Error('Not implemented');
}
