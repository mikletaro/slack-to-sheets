import os
import re
from datetime import datetime, timedelta, timezone

from slack_sdk import WebClient
from sheets_utils import get_worksheet

JST = timezone(timedelta(hours=9))


def extract_info_from_message(text: str):
    lines = [line.strip() for line in text.splitlines()]
    name = None
    bid = None

    for i, line in enumerate(lines):
        # 物件名の取得（"物件名:" の次の行を参照）
        if re.match(r"^物件名[:：]?$", line) and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line and not re.match(r"^物件ID[:：]?$", next_line):
                name = next_line

        # 物件IDの取得
        if re.match(r"^物件ID[:：]?$", line) and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if re.match(r"^\d+$", next_line):  # 数字だけの場合
                bid = next_line
            else:
                # URL形式から抽出
                bid_match = re.search(r"mansion/(\d+)", next_line)
                if bid_match:
                    bid = bid_match.group(1)

    # バックアップとして、本文全体から bid 抽出（URLリンク形式）
    if not bid:
        match = re.search(r"mansion/(\d+)\|", text)
        if match:
            bid = match.group(1)

    return name, bid


def get_monday_jst():
    today_jst = datetime.now(JST)
    monday = today_jst - timedelta(days=today_jst.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def fetch_slack_messages():
    client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
    channel_id = os.environ["SLACK_CHANNEL_ID"]
    oldest = get_monday_jst().timestamp()

    print(f"[INFO] Slack取得開始（今週月曜 JST）: {datetime.fromtimestamp(oldest, JST)}")

    response = client.conversations_history(channel=channel_id, oldest=oldest)
    messages = response["messages"]
    print(f"[INFO] 取得したSlackメッセージ数: {len(messages)}")

    records = []
    seen_bids = set()

    for msg in messages:
        ts = float(msg["ts"])
        dt = datetime.fromtimestamp(ts, JST)
        text = msg.get("text", "")
        name, bid = extract_info_from_message(text)
        date_str = dt.strftime("%Y-%m-%d")

        print(f"[SLACK] timestamp: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[SLACK] name: {name}, bid: {bid}, date: {date_str}")

        if bid and bid not in seen_bids:
            records.append((name, bid, date_str))
            seen_bids.add(bid)

    return records


def check_and_append_missing_entries():
    slack_records = fetch_slack_messages()
    if not slack_records:
        print("❌ Slackから有効な通知が取得できませんでした。")
        return

    ws = get_worksheet()
    sheet_rows = ws.get_all_values()
    sheet_bids = set(r[1] for r in sheet_rows[1:] if len(r) > 1 and r[1])

    missing = []

    for name, bid, date in slack_records:
        if bid not in sheet_bids:
            missing.append((name, bid, date))

    if missing:
        print("⚠️ スプレッドシートに記載されていない通知があります:")
        for name, bid, date in missing:
            print(f"- 日付: {date}, 物件名: {name}, 物件ID: {bid}")

        rows_to_append = [[name or "", bid, "", date] for name, bid, date in missing]
        ws.append_rows(rows_to_append, value_input_option="USER_ENTERED")
        print(f"📌 {len(rows_to_append)} 件をスプレッドシートに追記しました。")
    else:
        print("✅ 今週分の通知はすべて記載済みです。")


if __name__ == "__main__":
    check_and_append_missing_entries()
