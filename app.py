from flask import Flask, request, jsonify
from datetime import datetime
import re
from sheets_utils import append_if_not_duplicate

app = Flask(__name__)

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

        # 物件名とIDを抽出
        name_match = re.search(r"物件名:\s*(.+?)\n", text)
        id_match = re.search(r"物件ID:\s*(\d+)", text)

        if name_match and id_match:
            bukken_name = name_match.group(1).strip()
            bukken_id = id_match.group(1).strip()
            date = datetime.fromtimestamp(float(ts.split('.')[0])).strftime('%Y/%m/%d')
            append_if_not_duplicate(bukken_name, bukken_id, date)
        else:
            print("⚠️ 情報が見つかりませんでした")

    return "OK"
