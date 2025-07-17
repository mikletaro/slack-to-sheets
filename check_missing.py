import os
import re
from datetime import datetime, timedelta
import pytz
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from sheets_utils import append_row_if_not_exists

# 環境変数の読み込み
SLACK_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL_ID = os.environ["SLACK_CHANNEL_ID"]

# JSTの今週月曜0時を取得
def get_start_of_week_jst():
    jst = pytz.timezone("Asia/Tokyo")
    now = datetime.now(jst)
    start_of_week = now - timedelta(days=now.weekday())
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_of_week

# Slackメッセージ取得
def fetch_slack_messages():
    client = WebClient(token=SLACK_TOKEN)
    start_ts = get_start_of_week_jst().timestamp()
    messages = []

    try:
        response = client.conversations_history(
            channel=SLACK_CHANNEL_ID,
            oldest=str(start_ts),
            limit=100
        )
        messages.extend(response["messages"])
    except SlackApiError as e:
        print("Error fetching messages:", e)

    return messages

# メッセージ本文から物件名とIDと日付を抽出
def parse_slack_message(text):
    # 物件名: XXXXX
    name_match = re.search(r"物件名[:：]\s*(.+?)(?:\s|　|,|，|。|$)", text)
    # 物件ID: 123456
    bid_match = re.search(r"物件ID[:：]?\s*(\d+)", text)
    # 日付: 2025-07-16
    date_match = re.search(r"日付[:：]?\s*(\d{4}-\d{2}-\d{2})", text)

    name = name_match.group(1).strip() if name_match else None
    bid = bid_match.group(1).strip() if bid_match else None
    date = date_match.group(1).strip() if date_match else None

    return name, bid, date

# メイン処理
def check_missing_entries():
    messages = fetch_slack_messages()
    print(f"[INFO] 取得したSlackメッセージ数: {len(messages)}")

    missing_entries = []

    for msg in messages:
        ts = msg.get("ts")
        text = msg.get("text", "")
        name, bid, date_str = parse_slack_message(text)

        if not (name and bid and date_str):
            print(f"[SKIP] パースできないメッセージ: {ts}")
            continue

        print(f"[SLACK] timestamp: {datetime.fromtimestamp(float(ts)).strftime('%Y-%m-%d')}, name: {name}, bid: {bid}, date: {date_str}")

        row = [name, bid, "", date_str]
        success = append_row_if_not_exists(row, unique_cols=["物件名", "物件ID", "日付"])

        if success:
            missing_entries.append((name, bid, date_str))

    if missing_entries:
        print("⚠️ スプレッドシートに記載されていない通知があります:")
        for name, bid, date_str in missing_entries:
            print(f"- 日付: {date_str}, 物件名: {name}, 物件ID: {bid}")
        print(f"📌 {len(missing_entries)} 件をスプレッドシートに追記しました。")
    else:
        print("✅ 今週分の通知はすべて記載済みです。")

if __name__ == "__main__":
    print(f"[INFO] Slack取得開始（今週月曜 JST）: {get_start_of_week_jst()}")
    check_missing_entries()
