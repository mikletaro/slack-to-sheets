import os
import re
import requests
from datetime import datetime, timedelta
from sheets_utils import get_worksheet

SLACK_TOKEN = os.environ['SLACK_BOT_TOKEN']
CHANNEL_ID = os.environ['SLACK_CHANNEL_ID']

def get_slack_messages_past_week():
    now = datetime.now()
    oldest = int((now - timedelta(days=7)).timestamp())
    url = "https://slack.com/api/conversations.history"
    headers = {"Authorization": f"Bearer {SLACK_TOKEN}"}
    params = {
        "channel": CHANNEL_ID,
        "oldest": oldest,
        "limit": 200
    }
    res = requests.get(url, headers=headers, params=params).json()
    return res.get("messages", [])

def extract_bukken_info(text):
    name_match = re.search(r"物件名:\s*(.+?)\n", text)
    id_match = re.search(r"物件ID:\s*(\d+)", text)
    if name_match and id_match:
        return name_match.group(1).strip(), id_match.group(1).strip()
    return None, None

def check_missing_entries():
    messages = get_slack_messages_past_week()
    sheet_rows = get_worksheet().get_all_values()

    existing = {(row[0], row[1]) for row in sheet_rows if len(row) >= 2}
    missing = []

    for msg in messages:
        text = msg.get("text", "")
        name, bid = extract_bukken_info(text)
        if name and bid and (name, bid) not in existing:
            missing.append((name, bid))

    if missing:
        print("❌ 記載漏れがあります：")
        for name, bid in missing:
            print(f"- {name}（ID: {bid}）")
    else:
        print("✅ 今週分の通知はすべて記載済みです。")

if __name__ == "__main__":
    check_missing_entries()
