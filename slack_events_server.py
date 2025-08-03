# slack_events_server.py
import os
import datetime as dt
import re
import pytz
from typing import Optional, Tuple

from flask import Flask, request
from slack_bolt import App                             # pip install slack-bolt slack-sdk
from slack_bolt.adapter.flask import SlackRequestHandler

from sheets_utils import get_worksheet, append_row_if_not_exists
# ───────────────────────────────────────────
# ❶ Slack Bolt アプリ（署名検証・リトライ処理を自動化）
# ───────────────────────────────────────────
bolt_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
)

# --- 既存ロジックを使い回し ------------------
def extract_bid(text: str) -> str:
    m = re.search(r"\|(\d+)>", text)
    return m.group(1) if m else text.strip()

def parse_slack_message(event: dict) -> Optional[Tuple[str, str, str]]:
    """
    Slack メッセージから (物件名, 物件ID, YYYY-MM-DD) を取得。
    解析できなければ None。
    check_missing.py と同じ実装を転用してください。
    """
    ...

def record_if_missing(name: str, bid: str, date_str: str) -> None:
    ws = get_worksheet()
    existing = {(r[0], r[1]) for r in ws.get_all_values()[1:]}
    if (name, bid) in existing:
        return
    append_row_if_not_exists([name, bid, "", date_str])
    print(f"[WRITE] {name}, {bid}, {date_str}")

# ───────────────────────────────────────────
# ❷ イベントハンドラ
# ───────────────────────────────────────────
@bolt_app.event("message")
def handle_message_events(body, logger):
    event = body["event"]

    # ボットメッセージやスレッド返信をスキップ
    if event.get("subtype") == "bot_message" or event.get("thread_ts"):
        return

    parsed = parse_slack_message(event)
    if not parsed:
        logger.info(f"skip (unparsable): ts={event['ts']}")
        return

    name, bid, date_str = parsed
    logger.info(f"→ {name} / {bid} / {date_str}")
    record_if_missing(name, bid, date_str)

# ───────────────────────────────────────────
# ❸ Flask ラッパー（Render は gunicorn で起動）
# ───────────────────────────────────────────
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
