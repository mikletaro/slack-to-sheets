import os
import datetime
import pytz
import re
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

# 通知メッセージから情報抽出
def extract_info_from_message(text: str):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = None
    bid = None

    for i in range(len(lines)):
        line = lines[i]

        # 物件名の抽出（同一行 or 次の行）
        if "物件名" in line and not name:
            match = re.search(r"物件名[:：]?\s*(.+?)($|\s+\*?物件ID|物件ID[:：])", line)
            if match:
                name = match.group(1).strip()
            elif i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and "物件ID" not in next_line:
                    name = next_line.strip()

        # 物件IDの抽出（同一行 or 次の行）
        if "物件ID" in line and not bid:
            match = re.search(r"物件ID[:：]?\s*(\d+)", line)
            if match:
                bid = match.group(1).strip()
            elif i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line.isdigit():
                    bid = next_line

    return name, bid

# メイン処理
def check_missing_entries():
    messages = fetch_slack_messages()
    sheet_rows = get_worksheet().get_all_values()
    existing_entries = {(row[0], row[1]) for row in sheet_rows[1:]}

    missing = []

    for msg in messages:
        text = msg.get("text", "")
        ts = float(msg.get("ts", "0"))
        dt = datetime.datetime.fromtimestamp(ts, pytz.timezone("Asia/Tokyo")).date()
        name, bid = extract_info_from_message(text)

        print(f"[SLACK] timestamp: {dt}, name: {name}, bid: {bid}, date: {dt}")

        if bid and name and (name, bid) not in existing_entries:
            missing.append((dt.strftime("%Y-%m-%d"), name, bid))

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
