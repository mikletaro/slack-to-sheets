# slack-to-sheets

Slackからの通知を受信し、Googleスプレッドシートに記録するFlaskアプリ。

## 必要な環境変数

- `SPREADSHEET_ID`: Google SheetsのスプレッドシートID
- `SLACK_BOT_TOKEN`: SlackアプリのBot User OAuth Token (xoxb-で始まる)
- `SLACK_SIGNING_SECRET`: SlackアプリのSigning Secret
- `GOOGLE_CREDENTIALS_BASE64`: Google Sheets APIの認証情報(credentials.json)をBase64エンコードした文字列

## 手順(概要)

1. Slack App作成 → Events API 有効化、Bot Token Scopesを設定
2. `/slack/events` にRenderなどのデプロイ先URLを登録
3. 環境変数を設定（上記4つすべて）
4. デプロイ後、Slackで通知を受け取ると自動でスプレッドシートに記録される

## エンドポイント

- `GET /`: ヘルスチェック用
- `POST /slack/events`: Slackイベントを受信
