import os
import datetime
import pytz
import re
from typing import Optional, Tuple
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from sheets_utils import get_worksheet, append_row_if_not_exists

def get_start_date_jst():
    jst = pytz.timezone("Asia/Tokyo")
    # 7月1日（今年）に変更
    start_date = datetime.datetime(2025, 9, 1, 0, 0, 0, tzinfo=jst)
    return start_date
    
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

    start_time = get_start_date_jst()
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

# Slackメッセージの内容をパースして物件情報を抽出
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
                    bid = extract_bid(bid_line[1].strip())

        text = block.get("text", {}).get("text", "")
        if "物件名" in text and not name:
            match = re.search(r"物件名[:：]*\n?([^\n]+)", text)
            if match:
                name = match.group(1).strip()
        if "物件ID" in text and not bid:
            match = re.search(r"物件ID[:：]*\n?([^\n]+)", text)
            if match:
                bid = extract_bid(match.group(1).strip())

    ts = message.get("ts")
    if ts:
        timestamp = datetime.datetime.fromtimestamp(float(ts), pytz.timezone("Asia/Tokyo"))
        date = timestamp.strftime("%Y-%m-%d")

    if name and bid and date:
        return (name, bid, date)
    return None

# リンク付きのbidを正規のIDに変換
def extract_bid(text: str) -> str:
    match = re.search(r"\|(\d+)>", text)
    if match:
        return match.group(1)
    return text.strip()

# テキストから物件名とIDを抽出
def extract_info_from_message(text: str):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = None
    bid = None

    for i in range(len(lines)):
        line = lines[i]

        if "物件名" in line and not name:
            match = re.search(r"物件名[:：]?\s*(.+?)($|\s+\*?物件ID|物件ID[:：])", line)
            if match:
                name = match.group(1).strip()
            elif i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and "物件ID" not in next_line:
                    name = next_line.strip()

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
    seen = set()

    for msg in messages:
        ts = msg.get("ts", "")
        text = msg.get("text", "")
        dt = datetime.datetime.fromtimestamp(float(ts), pytz.timezone("Asia/Tokyo")).date()

        parsed = parse_slack_message(msg)
        if parsed:
            name, bid, date = parsed
        else:
            print(f"[SKIP] パースできないメッセージ: {ts}")
            name, bid = extract_info_from_message(text)
            if not (name and bid):
                continue
            date = dt.strftime("%Y-%m-%d")

        print(f"[SLACK] timestamp: {dt}, name: {name}, bid: {bid}, date: {date}")
        key = (name, bid)
        full_key = (name, bid, date)

        if key not in existing_entries and full_key not in seen:
            missing.append((date, name, bid))
            seen.add(full_key)

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
