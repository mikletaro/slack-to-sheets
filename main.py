import os
import re
import pytz
import datetime as dt
import logging
from typing import Optional, Tuple
from flask import Flask, request, jsonify
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from sheets_utils import append_if_not_duplicate

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Slack Boltアプリ初期化
bolt_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
)

# メッセージパース処理
def extract_bid(text: str) -> str:
    m = re.search(r"\|(\d+)>", text)
    return m.group(1) if m else text.strip()

def parse_slack_message(event: dict) -> Optional[Tuple[str, str, str, bool]]:
    """
    Slackメッセージから (物件名, 物件ID, YYYY/MM/DD, 来場予約フラグ) を取得。
    解析できなければ None。
    """
    blocks = event.get("blocks", [])
    text = event.get("text", "")
    name = None
    bid = None
    date = None
    is_visit_reservation = False
    
    # 来場予約判定
    if "来場予約" in text:
        is_visit_reservation = True
    
    # blocksから物件情報を抽出
    for block in blocks:
        # 来場予約チェック（blocks内）
        if not is_visit_reservation and "来場予約" in str(block):
            is_visit_reservation = True
        
        # fields から抽出
        for field in block.get("fields", []):
            text_content = field.get("text", "")
            if "物件名" in text_content and not name:
                name_line = text_content.split("\n")
                if len(name_line) > 1:
                    name = name_line[1].strip()
            elif "物件ID" in text_content and not bid:
                bid_line = text_content.split("\n")
                if len(bid_line) > 1:
                    bid = extract_bid(bid_line[1].strip())
        
        # text.text から抽出
        text_block = block.get("text", {}).get("text", "")
        if "物件名" in text_block and not name:
            match = re.search(r"物件名[:：]*\n?([^\n]+)", text_block)
            if match:
                name = match.group(1).strip()
        if "物件ID" in text_block and not bid:
            match = re.search(r"物件ID[:：]*\n?([^\n]+)", text_block)
            if match:
                bid = extract_bid(match.group(1).strip())
    
    # タイムスタンプから日付を取得
    ts = event.get("ts")
    if ts:
        timestamp = dt.datetime.fromtimestamp(float(ts), pytz.timezone("Asia/Tokyo"))
        date = timestamp.strftime("%Y/%m/%d")
    
    if name and bid and date:
        return (name, bid, date, is_visit_reservation)
    return None

@bolt_app.event("message")
def handle_message_events(body, logger):
    event = body["event"]
    
    # デバッグ: イベント全体をログ出力
    logger.info(f"[DEBUG] Received event: {event}")
    
    # スレッド返信をスキップ
    if event.get("thread_ts"):
        logger.info("[SKIP] Thread reply detected")
        return
    
    # デバッグ: パース前の情報
    logger.info(f"[DEBUG] Event text: {event.get('text', '')}")
    logger.info(f"[DEBUG] Event blocks: {event.get('blocks', [])}")
    
    parsed = parse_slack_message(event)
    if not parsed:
        logger.warning(f"[PARSE_FAILED] Could not parse message - ts={event['ts']}")
        logger.warning(f"[PARSE_FAILED] Text: {event.get('text', '')}")
        logger.warning(f"[PARSE_FAILED] Blocks: {event.get('blocks', [])}")
        return
    
    name, bid, date_str, is_visit = parsed
    logger.info(f"[PARSED] 物件名={name} / 物件ID={bid} / 日付={date_str} / 来場予約={is_visit}")
    
    try:
        # sheets_utils の append_if_not_duplicate を使用
        result = append_if_not_duplicate(name, bid, date_str, is_visit_reservation=is_visit)
        if result:
            logger.info(f"[SUCCESS] Written to sheet: {name}, {bid}, {date_str}, 来場予約={is_visit}")
        else:
            logger.info(f"[DUPLICATE] Already exists: {name}, {bid}")
    except Exception as e:
        logger.error(f"[ERROR] Failed to write to sheet: {e}")
        logger.error(f"[ERROR] Data: name={name}, bid={bid}, date={date_str}, visit={is_visit}")
        raise

flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)

# 全リクエストをログに記録
@flask_app.before_request
def log_request_info():
    logger.info(f"[REQUEST] {request.method} {request.path} from {request.remote_addr}")
    if request.method == "POST":
        logger.info(f"[REQUEST] Content-Type: {request.content_type}")

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    # Slackの再送をスキップ（3秒以内にACKを返せなかった場合の再送）
    retry_num = request.headers.get("X-Slack-Retry-Num")
    if retry_num:
        logger.info(f"[SKIP] Slack retry detected (retry #{retry_num})")
        return "", 200

    logger.info("[SLACK_EVENT] Slack event received")
    return handler.handle(request)

@flask_app.route("/", methods=["GET"])
def index():
    return "Slack → Sheets bridge is running!"

@flask_app.route("/health", methods=["GET"])
def health_check():
    """診断用ヘルスチェックエンドポイント"""
    env_status = {
        "SLACK_BOT_TOKEN": "✅ 設定済み" if os.environ.get("SLACK_BOT_TOKEN") else "❌ 未設定",
        "SLACK_SIGNING_SECRET": "✅ 設定済み" if os.environ.get("SLACK_SIGNING_SECRET") else "❌ 未設定",
        "GOOGLE_CREDENTIALS_BASE64": "✅ 設定済み" if os.environ.get("GOOGLE_CREDENTIALS_BASE64") else "❌ 未設定",
        "SPREADSHEET_ID": "✅ 設定済み" if os.environ.get("SPREADSHEET_ID") else "❌ 未設定",
    }
    
    all_set = all("✅" in v for v in env_status.values())
    
    return jsonify({
        "status": "healthy" if all_set else "configuration_error",
        "environment_variables": env_status,
        "message": "全ての環境変数が設定されています" if all_set else "一部の環境変数が未設定です"
    })

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("[STARTUP] Slack → Sheets アプリを起動します")
    logger.info(f"[STARTUP] PORT: {os.environ.get('PORT', 3000)}")
    logger.info("=" * 60)
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
