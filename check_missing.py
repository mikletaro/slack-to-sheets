import os
import re
from datetime import datetime, timedelta, timezone

from slack_sdk import WebClient
from sheets_utils import get_worksheet

# JST（日本時間）
JST = timezone(timedelta(hours=9))


def extract_info_from_message(text: str):
    """行ごとに分割されたSlack通知メッセージから物件名と物件IDを抽出"""
    lines = text.splitlines()
    name = None
    bid = None

    for i, line in enumerate(lines):
        if "物件名" in line and i + 1 < len(lines):
            name = lines[i + 1].strip()
        elif "物件ID" in line and i + 1 < len(lines):
            bid = lines[i + 1].strip()
    return name, bid


def get_monday_jst():
    """今週月曜 0:00 JST を取得"""
    today_jst = datetime.now(JST)
    monday = today_jst - timedelta(days=today_jst.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def fetch_slack_messages():
    """Slack APIから今週分のメッセージを取得"""
    client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    channel_id = os.environ["SLACK_CHANNEL_ID"]
    oldest = get_monday_jst().timestamp()

    print(f"[INFO] Slack取得開始（今週月曜 JST）: {datetime.fromtimestamp(oldest, JST)}")

    response = client.conversations_history(channel=channel_id, oldest=oldest)
    messages = response["messages"]

    print(f"[INFO] 取得したSlackメッセージ数: {len(messages)}")

    records = []

    for msg in messages:
        ts = float(msg["ts"])
        dt = datetime.fromtimestamp(ts, JST)
        text = msg.get("text", "")
        name, bid = extract_info_from_message(text)

        date_str = dt.strftime("%Y-%m-%d")

        print(f"[SLACK] timestamp: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[SLACK] name: {name}, bid: {bid}, date: {date_str}")

        if name and bid:
            records.append((name, bid, date_str))

    return records


def check_missing_entries():
    """Slackとスプレッドシートを比較し、未記載エントリを出力"""
    slack_records = fetch_slack_messages()

    if not slack_records:
        print("❌ Slackから有効な通知が取得できませんでした。")
        return

    sheet_rows = get_worksheet().get_all_values()
    sheet_records = set((r[0], r[1], r[3]) for r in sheet_rows[1:] if len(r) >= 4)

    missing = []

    for name, bid, date in slack_records:
        if (name, bid, date) not in sheet_records:
            missing.append((name, bid, date))

    if missing:
        print("⚠️ スプレッドシートに記載されていない通知があります:")
        for name, bid, date in missing:
            print(f"- 日付: {date}, 物件名: {name}, 物件ID: {bid}")
    else:
        print("✅ 今週分の通知はすべて記載済みです。")


if __name__ == "__main__":
    check_missing_entries()
