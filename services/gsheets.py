import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import SPREADSHEET_ID, CREDENTIALS_PATH
from datetime import datetime

def get_sheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"❌ GSheets ulanish xatosi: {e}")
        return None

def sync_new_remnant(data):
    """Yangi qoldiqni Sheetga yozish (A-M ustunlar)"""
    client = get_sheet_client()
    if not client: return
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
        hozirgi_vaqt = datetime.now().strftime("%d.%m.%Y %H:%M")
        row = [
            f"#{data.get('id')}", hozirgi_vaqt, data.get('category'), data.get('material'),
            data.get('width'), data.get('height'), data.get('qty'), data.get('origin_order'),
            data.get('user_name'), str(data.get('user_id')), data.get('location'), 1, ""
        ] + [""] * 4 # N, O, P, Q ustunlar bo'sh
        sheet.append_row(row)
    except Exception as e: print(f"❌ Sheetga yozishda xato: {e}")

def sync_new_user(user_id, full_name):
    """Yangi userni Ruxsatlar varag'iga yozish"""
    client = get_sheet_client()
    if not client: return
    try:
        sheet = client.open_by_key(SPREADSHEET_ID).get_worksheet(1)
        if str(user_id) not in sheet.col_values(1):
            sheet.append_row([str(user_id), full_name, 0, 0, 0, 0, 0])
    except Exception as e: print(f"❌ Userni sheetga yozishda xato: {e}")

def get_all_users_from_sheet():
    """Ruxsatlarni o'qish (2-sahifa)"""
    client = get_sheet_client()
    if not client: return []
    try:
        return client.open_by_key(SPREADSHEET_ID).get_worksheet(1).get_all_values()[1:]
    except: return []

def get_all_remnants_from_sheet():
    """Qoldiqlarni o'qish (1-sahifa)"""
    client = get_sheet_client()
    if not client: return []
    try:
        return client.open_by_key(SPREADSHEET_ID).get_worksheet(0).get_all_values()[1:]
    except: return []
