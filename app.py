from flask import Flask, request, jsonify
from sheets_utils import append_to_sheet, already_exists
import os
import datetime
import re

app = Flask(__name__)

SLACK_VERIFICATION_TOKEN = os.environ.get("SLACK_VERIFICATION_TOKEN")

@app.route("/events", methods=["POST"])
def slack_events():
    payload = request.json

    # Slack URL Verification
    if payload.get("type") == "url_verification":
        return jsonify({"challenge": payload["challenge"]})

    # Basic event validation
    event = payload.get("event", {})
    if event.get("type") != "message" or "bot_id" not in event:
        return "", 200  # Ignore user messages or other events

    text = event.get("text", "")
    property_name, property_id = extract_info(text)
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    if not property_id:
        return "No property ID found", 200

    if already_exists(property_id):
        return f"Property ID {property_id} already exists", 200

    append_to_sheet(property_name, property_id, today)
    return "OK", 200

def extract_info(text):
    lines = text.strip().splitlines()
    name = lines[0].strip() if lines else ""

    id_match = re.search(r"物件ID[:：]?\s*(\d+)", text)
    prop_id = id_match.group(1) if id_match else ""

    return name, prop_id

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

