This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## 環境変数

API 呼び出し先のベース URL をフロントで参照できるよう、`NEXT_PUBLIC_API_BASE` を設定します。

```bash
# frontend/.env.local
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

- 例: ローカルの FastAPI が `http://localhost:8000` の場合
- `NEXT_PUBLIC_` で始まる変数のみブラウザから参照可能です
- `Content-Type` は手動で設定せず、ブラウザに任せてください（`FormData` 利用時の定石）

## API 動作確認 (cURL)

バックエンドの `/subtitles/en` エンドポイントを cURL で検証できます。

```bash
API_BASE=${NEXT_PUBLIC_API_BASE:-http://localhost:8000}
curl -X POST \
  "$API_BASE/subtitles/en" \
  -H "Accept: video/mp4" \
  -F "file=@/path/to/input.mp4" \
  -o output_subs.mp4
```

メモ:

- `Content-Type` は指定しません（`-F` によりmultipartのboundaryは自動付与されます）
- 拡張子は `{mp4, mov, mkv, webm, m4v}` を推奨
- 大容量の場合は時間がかかるため、十分なタイムアウト設定や再試行方針を検討してください

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
