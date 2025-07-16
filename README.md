# slack-to-sheets

Slackからの通知を受信し、Googleスプレッドシートに記録するFlaskアプリ。

## 必要な環境変数

- `SPREADSHEET_ID`: Google SheetsのスプレッドシートID
- `SLACK_VERIFICATION_TOKEN`: SlackのEvents API用検証トークン

## 手順（概要）

1. Slack App作成 → Events API 有効化
2. `/events` にRenderのURLを登録
3. Google Sheets APIの認証情報（credentials.json）を同梱 or RenderのDiskにアップ

