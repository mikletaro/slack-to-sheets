from flask import Flask, request, jsonify
from datetime import datetime
import pytz
import re
from sheets_utils import append_if_not_duplicate

app = Flask(__name__)

def extract_info_from_blocks(blocks):
    name = None
    bid = None
    for block in blocks:
        for field in block.get("fields", []):
            text = field.get("text", "")
            if "物件名" in text and not name:
                lines = text.split("\n")
                if len(lines) > 1:
                    name = lines[1].strip()
            elif "物件ID" in text and not bid:
                lines = text.split("\n")
                if len(lines) > 1:
                    bid = extract_bid(lines[1].strip())

        text_block = block.get("text", {}).get("text", "")
        if "物件名" in text_block and not name:
            match = re.search(r"物件名[:：]*\n?([^\n]+)", text_block)
            if match:
                name = match.group(1).strip()
        if "物件ID" in text_block and not bid:
            match = re.search(r"物件ID[:：]*\n?([^\n]+)", text_block)
            if match:
                bid = extract_bid(match.group(1).strip())

    return name, bid

def extract_bid(text: str) -> str:
    match = re.search(r"\|(\d+)>", text)
    if match:
        return match.group(1)
    return text.strip()

@app.route("/")
def home():
    return "Slack to Sheets app is running."

@app.route("/events", methods=["POST"])
def slack_events():
    data = request.json

    # URL検証
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data["challenge"]})

    # メッセージイベントの処理
    if data.get("type") == "event_callback":
        event = data["event"]
        text = event.get("text", "")
        ts = event.get("ts", "")
        blocks = event.get("blocks", [])

        name = None
        bid = None

        # blocks優先で抽出
        if blocks:
            name, bid = extract_info_from_blocks(blocks)

        # blocksで取れない場合はtextをfallbackで使う
        if not (name and bid):
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            for i in range(len(lines)):
                if "物件名" in lines[i] and not name:
                    if i + 1 < len(lines):
                        name = lines[i + 1].strip()
                if "物件ID" in lines[i] and not bid:
                    if i + 1 < len(lines):
                        bid = extract_bid(lines[i + 1].strip())

        if name and bid and ts:
            dt = datetime.fromtimestamp(float(ts), pytz.timezone("Asia/Tokyo"))
            date = dt.strftime('%Y/%m/%d')
            append_if_not_duplicate(name, bid, date)
        else:
            print("⚠️ 情報が見つかりませんでした")
            print(f"[DEBUG] text={text}")
            print(f"[DEBUG] blocks={blocks}")

    return "OK"

# ✅ Render用エントリーポイント
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
