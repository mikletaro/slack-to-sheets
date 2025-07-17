import os
import re
from datetime import datetime, timedelta
import pytz
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from sheets_utils import append_if_not_duplicate

SLACK_TOKEN = os.environ["SLACK_BOT_TOKEN"]
CHANNEL_ID = os.environ["SLACK_CHANNEL_ID"]

def parse_slack_message(text):
    results = []
    lines = text.split('\n')
    bid_pattern = re.compile(r'(物件ID[:：]?\s*(\d+))')
    date_pattern = re.compile(r'(\d{4}-\d{2}-\d{2})')
    
    bukken_name = None
    bukken_id = None
    date_str = None

    for line in lines:
        bid_match = bid_pattern.search(line)
        date_match = date_pattern.search(line)
        
        if bid_match:
            bukken_id = bid_match.group(2)
        if date_match:
            date_str = date_match.group(1)
        
        # 「*物件ID:* 123456」のような形式を除外して物件名とみなす
        if '物件ID' not in line and '日付' not in line and date_pattern.search(line) is None:
            bukken_name = line.strip()
        
        if bukken_name and bukken_id and date_str:
            results.append((bukken_name, bukken_id, date_str))
            bukken_name = bukken_id = date_str = None  # リセットして次の行に対応

    return results

def get_this_week_start_jst():
    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst)
    monday = now - timedelta(days=now.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    return monday

def fetch_slack_messages():
    client = WebClient(token=SLACK_TOKEN)
    start_time = get_this_week_start_jst().timestamp()
    messages = []
    has_more = True
    cursor = None

    print("[INFO] Slack取得開始（今週月曜 JST）:", get_this_week_start_jst())

    try:
        while has_more:
            response = client.conversations_history(
                channel=CHANNEL_ID,
                oldest=str(start_time),
                limit=200,
                cursor=cursor
            )
            messages.extend(response["messages"])
            has_more = response.get("has_more", False)
            cursor = response.get("response_metadata", {}).get("next_cursor", None)
    except SlackApiError as e:
        print(f"[ERROR] Slack API error: {e.response['error']}")
    
    print("[INFO] 取得したSlackメッセージ数:", len(messages))
    return messages

def check_missing_entries():
    messages = fetch_slack_messages()
    new_entries = []

    for msg in messages:
        text = msg.get("text", "")
        ts = msg.get("ts", "")
        try:
            parsed_entries = parse_slack_message(text)
            if not parsed_entries:
                print(f"[SKIP] パースできないメッセージ: {ts}")
                continue
            for name, bid, date_str in parsed_entries:
                print(f"[SLACK] timestamp: {ts}, name: {name}, bid: {bid}, date: {date_str}")
                success = append_if_not_duplicate(name, bid, date_str)
                if success:
                    new_entries.append((name, bid, date_str))
        except Exception as e:
            print(f"[ERROR] メッセージ処理中の例外: {e}, ts: {ts}")
    
    if new_entries:
        print("⚠️ スプレッドシートに記載されていない通知があります:")
        for name, bid, date_str in new_entries:
            print(f"- 日付: {date_str}, 物件名: {name}, 物件ID: {bid}")
        print(f"📌 {len(new_entries)} 件をスプレッドシートに追記しました。")
    else:
        print("✅ 今週分の通知はすべて記載済みです。")

if __name__ == "__main__":
    check_missing_entries()
