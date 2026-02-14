import os
import base64
import json
import gspread
from google.oauth2.service_account import Credentials

def get_worksheet():
    # Base64環境変数からサービスアカウント認証
    creds_json = base64.b64decode(os.environ['GOOGLE_CREDENTIALS_BASE64']).decode('utf-8')
    creds_dict = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(credentials)

    # スプレッドシートID取得してワークシート選択
    sheet_id = os.environ['SPREADSHEET_ID']
    spreadsheet = client.open_by_key(sheet_id)
    return spreadsheet.worksheet("テストログ")

def append_if_not_duplicate(bukken_name, bukken_id, date_str, is_visit_reservation=False):
    ws = get_worksheet()
    records = ws.get_all_values()

    # 来場予約の場合、物件IDで既存行を検索
    if is_visit_reservation:
        for idx, row in enumerate(records):
            # B列(物件ID)で一致をチェック（物件名は表記揺れがあるためIDで統一）
            if len(row) >= 2 and row[1].strip() == str(bukken_id).strip():
                # 既存行が見つかった場合、H列(インデックス7)を更新
                row_number = idx + 1  # gspreadは1-indexed
                ws.update_cell(row_number, 8, "1")  # H列は8番目
                print(f"✅ Updated H column for existing property: {bukken_name} (ID: {bukken_id})")
                return True

        # 既存行が見つからない場合、新しい行を追加
        row_data = [bukken_name, bukken_id, "", date_str, "", "", "", "1"]
        ws.append_row(row_data)
        print("✅ Appended new visit reservation:", bukken_name, bukken_id, date_str)
        return True
    
    # 来場予約でない場合、物件IDで重複チェック(既存の動作)
    for row in records:
        if len(row) >= 2 and row[1].strip() == str(bukken_id).strip():
            print("🟡 Duplicate entry found. Skipping.")
            return False

    row_data = [bukken_name, bukken_id, "", date_str]
    ws.append_row(row_data)
    print("✅ Appended to sheet:", bukken_name, bukken_id, date_str)
    return True

def append_row_if_not_exists(row, unique_cols=None):
    """
    worksheet引数を省略し、内部でget_worksheet()を使用。
    `unique_cols`を指定すると、重複チェックにカラム名で比較。
    """
    worksheet = get_worksheet()
    all_values = worksheet.get_all_values()

    if not all_values:
        worksheet.append_row(row)
        return True

    headers = all_values[0]
    data = all_values[1:]

    if unique_cols:
        indices = [headers.index(col) for col in unique_cols if col in headers]
        for existing_row in data:
            if all(existing_row[i] == row[i] for i in indices):
                print("🟡 Duplicate row based on unique_cols. Skipping.")
                return False
    elif row in data:
        print("🟡 Exact row already exists. Skipping.")
        return False

    worksheet.append_row(row)
    print("✅ Appended to sheet:", row)
    return True
