# slack-to-sheets - Slack通知→Google Sheets自動記録

## 概要

Slackの通知をリアルタイムで受信し、Google Sheetsに自動記録するブリッジアプリです。物件名・物件ID・日付を自動抽出し、来場予約フラグの判定や重複チェックも行います。`check_missing.py` で過去メッセージの遡及追記も可能です。

## 技術スタック

- Python
- Flask
- Slack Bolt
- gspread / google-auth
- gunicorn
- デプロイ先: Render（PaaS）

## セットアップ

以下の環境変数を設定してください。

| 環境変数 | 説明 |
|---------|------|
| `SPREADSHEET_ID` | 対象スプレッドシートのID |
| `SLACK_BOT_TOKEN` | Slack Botトークン |
| `SLACK_SIGNING_SECRET` | Slack署名シークレット |
| `GOOGLE_CREDENTIALS_BASE64` | GCPサービスアカウント認証情報（Base64） |
render.comにmikletaroアカウントがあります。google認証で入れます。
Slack AppのEvent SubscriptionsでRequest URLに `https://your-app/slack/events` を設定してください。

## 使い方

- Slackに通知が来ると自動でスプレッドシートに記録されます
- 過去メッセージを遡及追記する場合は `check_missing.py` を実行してください

```bash
python check_missing.py
```
