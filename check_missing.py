import os
import re
import logging
from datetime import datetime, timedelta, timezone

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from sheets_utils import get_worksheet

logging.basicConfig(level=logging.INFO, format="%(message)s")

JST = timezone(timedelta(hours=9))


def extract_info_from_text(text):
    name_match = re.search(r"物件名[：:]\s*(.+)", text)
    bid_match = re.search(r"物件ID[：:]\s*(\S+)", text)
    date_match = re.search(r"(\d{4}/\d{2}/\d{2})", text)

    name = name_match.group(1).strip() if name_match else None
    bid = bid_match.group(1).strip() if bid_match else None
    date_str = date_match.group(1) if date_match else None

    return name, bid, date_str


def fetch_slack_messages():
    token = os.environ["SLACK_BOT_TOKEN"]
    channel_id = os.environ["SLACK_CHANNEL_ID"]
    client = WebClient(token=token)

    today_jst = datetime.now(JST).replace(hour=0, minute=0, second=0, microsecond=0)
    this_week_start = today_jst - timedelta(days=today_jst.weekday())
    this_week_start_utc_ts = this_week_start.astimezone(timezone.utc).timestamp()

    logging.info(f"[INFO] Slack取得開始（今週月曜 JST）: {this_week_start.strftime('%Y-%m-%d %H:%M:%S')}")

    messages = []
    try:
        result = client.conversations_history(
            channel=channel_id,
            oldest=this_week_start_utc_ts,
            limit=1000
        )
        messages = result.get("messages", [])
        logging.info(f"[INFO] 取得したSlackメッセージ数: {len(messages)}")

    except SlackApiError as e:
        logging.error(f"[ERROR] Slack APIエラー: {e}")

    return messages


def check_missing_entries():
    sheet_rows = get_worksheet().get_all_values()
    sheet_keys = set()

    for row in sheet_rows[1:]:  # Skip header
        name, bid, date = row[0], row[1], row[3]
        if name and bid and date:
            sheet_keys.add((name, bid, date))

    messages = fetch_slack_messages()
    missing_entries = []

    for message in messages:
        text = message.get("text", "")
        ts = float(message.get("ts", "0"))
        dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(JST)
        timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        name, bid, date = extract_info_from_text(text)
        logging.info(f"[SLACK] timestamp: {timestamp_str}")
        logging.info(f"[SLACK] name: {name}, bid: {bid}, date: {date}")

        if name and bid and date and (name, bid, date) not in sheet_keys:
            missing_entries.append((name, bid, date))

    if missing_entries:
        logging.warning("⚠️ 以下の通知がスプレッドシートに記載されていません：")
        for entry in missing_entries:
            logging.warning(f"- 物件名: {entry[0]}, 物件ID: {entry[1]}, 日付: {entry[2]}")
    else:
        logging.info("✅ 今週分の通知はすべて記載済みです。")


if __name__ == "__main__":
    check_missing_entries()
