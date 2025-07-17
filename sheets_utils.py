import os
import base64
import gspread
from google.oauth2.service_account import Credentials

def get_worksheet():
    # Renderでは環境変数から取得したBase64文字列をデコードしてcredentials.jsonとして扱う
    creds_json = base64.b64decode(os.environ['GOOGLE_CREDENTIALS_BASE64']).decode('utf-8')
    creds_dict = eval(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(credentials)

    # スプレッドシートのIDを環境変数から取得
    sheet_id = os.environ['SPREADSHEET_ID']
    spreadsheet = client.open_by_key(sheet_id) 
    
    return spreadsheet.worksheet("テストログ")

def append_if_not_duplicate(bukken_name, bukken_id, date_str):
    ws = get_worksheet()
    records = ws.get_all_values()

    for row in records:
        if len(row) >= 2 and row[0] == bukken_name and row[1] == bukken_id:
            print("🟡 Duplicate entry found. Skipping.")
            return False

    ws.append_row([bukken_name, bukken_id, "", date_str])
    print("✅ Appended to sheet:", bukken_name, bukken_id, date_str)
    return True


def append_row_if_not_exists(worksheet, row, unique_cols=None):
    # 例: unique_cols=['物件名', '物件ID', '日付']
    existing_values = worksheet.get_all_values()
    headers = existing_values[0]
    data = existing_values[1:]

    if unique_cols:
        indices = [headers.index(col) for col in unique_cols if col in headers]
        for existing_row in data:
            if all(existing_row[i] == row[i] for i in indices):
                return False  # 重複あり
    worksheet.append_row(row)
    return True
