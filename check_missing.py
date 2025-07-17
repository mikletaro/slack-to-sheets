import os
import datetime
import pytz
import re
from typing import Optional, Tuple
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from sheets_utils import get_worksheet, append_row_if_not_exists

# JSTで今週の月曜を取得
def get_start_of_week_jst():
    jst = pytz.timezone("Asia/Tokyo")
    now = datetime.datetime.now(jst)
    monday = now - datetime.timedelta(days=now.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    return monday

# Slackメッセージを取得
def fetch_slack_messages():
    token = os.environ["SLACK_BOT_TOKEN"]
    channel_id = os.environ["SLACK_CHANNEL_ID"]
    client = WebClient(token=token)

    start_time = get_start_of_week_jst()
    oldest_ts = start_time.timestamp()
    print(f"[INFO] Slack取得開始（今週月曜 JST）: {start_time}")

    try:
        response = client.conversations_history(
            channel=channel_id,
            oldest=str(oldest_ts),
            limit=1000,
        )
        messages = response["messages"]
        print(f"[INFO] 取得したSlackメッセージ数: {len(messages)}")
        return messages
    except SlackApiError as e:
        print(f"[ERROR] Slack API error: {e.response['error']}")
        return []

# Slackメッセージから物件名・ID・日付を抽出
def parse_slack_message(message: dict) -> Optional[Tuple[str, str, str]]:
    blocks = message.get("blocks", [])
    name = None
    bid = None
    date = None

    for block in blocks:
        for field in block.get("fields", []):
            text = field.get("text", "")
            if "物件名" in text:
                name_line = text.split("\n")
                if len(name_line) > 1:
                    name = name_line[1].strip()
            elif "物件ID" in text:
                bid_line = text.split("\n")
                if len(bid_line) > 1:
                    bid = bid_line[1].strip()

        text = block.get("text", {}).get("text", "")
        if "物件名" in text and not name:
            match = re.search(r"物件名[:：]*\n?([^\n]+)", text)
            if match:
                name = match.group(1).strip()
        if "物件ID" in text and not bid:
            match = re.search(r"物件ID[:：]*\n?(\d+)", text)
            if match:
                bid = match.group(1).strip()

    ts = message.get("ts")
    if ts:
        timestamp = datetime.datetime.fromtimestamp(float(ts), pytz.timezone("Asia/Tokyo"))
        date = timestamp.strftime("%Y-%m-%d")

    if name and bid and date:
        return (name, bid, date)
    return None

# メイン処理
def check_missing_entries():
    messages = fetch_slack_messages()
    sheet_rows = get_worksheet().get_all_values()
    existing_entries = {(row[0], row[1]) for row in sheet_rows[1:]}

    missing = []

    for msg in messages:
        parsed = parse_slack_message(msg)
        if parsed:
            name, bid, date = parsed
            print(f"[SLACK] timestamp: {date}, name: {name}, bid: {bid}, date: {date}")
            if (name, bid) not in existing_entries:
                missing.append((date, name, bid))
        else:
            ts = msg.get("ts", "unknown")
            print(f"[SKIP] パースできないメッセージ: {ts}")

    if not missing:
        print("✅ 今週分の通知はすべて記載済みです。")
    else:
        print("⚠️ スプレッドシートに記載されていない通知があります:")
        for date_str, name, bid in missing:
            print(f"- 日付: {date_str}, 物件名: {name}, 物件ID: {bid}")
            append_row_if_not_exists([name, bid, "", date_str])

        print(f"📌 {len(missing)} 件をスプレッドシートに追記しました。")

if __name__ == "__main__":
    check_missing_entries()
