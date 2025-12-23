import os
import re
import pytz
import datetime as dt
from typing import Optional, Tuple
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from sheets_utils import get_worksheet, append_row_if_not_exists

# Slack Boltアプリ初期化
bolt_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
)

# メッセージパース処理（check_missing.pyの関数と同様に実装）
def extract_bid(text: str) -> str:
    m = re.search(r"\|(\d+)>", text)
    return m.group(1) if m else text.strip()

def parse_slack_message(event: dict) -> Optional[Tuple[str, str, str]]:
    blocks = event.get("blocks", [])
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
    ts = event.get("ts")
    if ts:
        timestamp = dt.datetime.fromtimestamp(float(ts), pytz.timezone("Asia/Tokyo"))
        date = timestamp.strftime("%Y-%m-%d")
    if name and bid and date:
        return (name, bid, date)
    return None

def record_if_missing(name: str, bid: str, date_str: str) -> None:
    ws = get_worksheet()
    existing = {(r[0], r[1]) for r in ws.get_all_values()[1:]}
    if (name, bid) in existing:
        return
    append_row_if_not_exists([name, bid, "", date_str])
    print(f"[WRITE] {name}, {bid}, {date_str}")

@bolt_app.event("message")
def handle_message_events(body, logger):
    event = body["event"]
    if event.get("subtype") == "bot_message" or event.get("thread_ts"):
        return
    parsed = parse_slack_message(event)
    if not parsed:
        logger.info(f"skip (unparsable): ts={event['ts']}")
        return
    name, bid, date_str = parsed
    logger.info(f"→ {name} / {bid} / {date_str}")
    record_if_missing(name, bid, date_str)

flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

@flask_app.route("/", methods=["GET"])
def index():
    return "Slack → Sheets bridge is running!"

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))

