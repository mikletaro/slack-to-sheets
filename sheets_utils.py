import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
SHEET_NAME = os.environ.get("SHEET_NAME", "シート1")  # 任意に変更

def _get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    return sheet

def already_exists(property_id):
    sheet = _get_sheet()
    existing_ids = sheet.col_values(2)  # B列（物件ID）
    return property_id in existing_ids

def append_to_sheet(name, property_id, date):
    sheet = _get_sheet()
    sheet.append_row([name, property_id, '', date])

