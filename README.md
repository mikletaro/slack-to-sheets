# slack-to-sheets

Slackからの通知を受信し、Googleスプレッドシートに記録するFlaskアプリ。

## 必要な環境変数

- `SPREADSHEET_ID`: Google SheetsのスプレッドシートID
- `SLACK_BOT_TOKEN`: SlackアプリのBot User OAuth Token (xoxb-で始まる)
- `SLACK_SIGNING_SECRET`: SlackアプリのSigning Secret
- `GOOGLE_CREDENTIALS_BASE64`: Google Sheets APIの認証情報(credentials.json)をBase64エンコードした文字列

## 手順(概要)

1. **Slack App作成**
   - [Slack API](https://api.slack.com/apps)にアクセスして新しいアプリを作成
   - **Event Subscriptions**を有効化
   - **Bot Token Scopes**に以下を追加：
     - `channels:history`
     - `channels:read`
     - `chat:write`
   - **Subscribe to bot events**に`message.channels`を追加

2. **デプロイ先URL設定**
   - Renderなどにデプロイ後、`https://your-app.onrender.com/slack/events`をSlackアプリの**Request URL**に設定

3. **環境変数を設定**
   - 上記4つの環境変数をすべて設定（Renderの場合はダッシュボードから設定）

4. **動作確認**
   - Slackで通知を受け取ると自動でスプレッドシートに記録される
   - 「来場予約」を含むメッセージは、H列に「1」が記録される

## エンドポイント

- `GET /`: ヘルスチェック用
- `POST /slack/events`: Slackイベントを受信

## ローカル開発

```bash
# 依存関係のインストール
pip install -r requirements.txt

# 環境変数を設定（.envファイルを作成）
# .env.exampleを参考に必要な値を設定

# サーバー起動
python main.py

# ngrokなどで公開URLを取得し、Slackアプリの設定で一時的にそのURLを使用
ngrok http 3000
```

## トラブルシューティング

### 通知が記録されない場合

1. **Slackアプリの設定を確認**
   - Request URLが正しく設定されているか（`/slack/events`エンドポイント）
   - Event Subscriptionsが有効化されているか
   - Bot Token Scopesが正しく設定されているか

2. **環境変数を確認**
   - すべての環境変数が正しく設定されているか
   - `GOOGLE_CREDENTIALS_BASE64`が正しくBase64エンコードされているか

3. **ログを確認**
   - Renderなどのログを確認して、エラーメッセージがないか確認
