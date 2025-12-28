import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import SPREADSHEET_ID, CREDENTIALS_PATH
from datetime import datetime

# === USTUNLAR A–Q ===
COL = {
    "id": 1, "category": 2, "material": 3, "width": 4, "height": 5,
    "qty": 6, "order": 7, "location": 8, "status": 9,
    "image_id": 10, "created_user_id": 11, "created_user_name": 12,
    "created_at": 13, "used_user_id": 14, "used_user_name": 15,
    "used_for_order": 16, "used_at": 17
}

def get_sheet_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            CREDENTIALS_PATH, scope
        )
        return gspread.authorize(creds)
    except Exception as e:
        print(f"❌ GSheets error: {e}")
        return None

def sync_new_remnant(data):
    client = get_sheet_client()
    if not client:
        return

    sheet = client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    rid = data.get("id")
    if not rid:
        return

    row = [
        f"#{rid}",
        data.get("category", ""),
        data.get("material", ""),
        data.get("width", 0),
        data.get("height", 0),
        data.get("qty", 1),
        data.get("order", ""),
        data.get("location", ""),
        1,
        "",
        str(data.get("user_id", "")),
        data.get("user_name", ""),
        now,
        "", "", "", ""
    ]

    sheet.append_row(row, value_input_option="USER_ENTERED")

def mark_as_used_in_sheet(remnant_id, user_id, user_name, order_for):
    client = get_sheet_client()
    if not client:
        return

    sheet = client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
    cell = sheet.find(f"#{remnant_id}")
    if not cell:
        return

    row = cell.row
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    sheet.update_cell(row, COL["status"], 0)
    sheet.update(f"N{row}:Q{row}", [[str(user_id), user_name, order_for, now]])

def update_sheet_qty(remnant_id, new_qty):
    client = get_sheet_client()
    if not client:
        return

    sheet = client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
    cell = sheet.find(f"#{remnant_id}")
    if cell:
        sheet.update_cell(cell.row, COL["qty"], new_qty)

def update_sheet_status(remnant_id, status):
    client = get_sheet_client()
    if not client:
        return

    sheet = client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
    cell = sheet.find(f"#{remnant_id}")
    if cell:
        sheet.update_cell(cell.row, COL["status"], status)

def get_all_users_from_sheet():
    client = get_sheet_client()
    if not client:
        return []
    return client.open_by_key(SPREADSHEET_ID).get_worksheet(1).get_all_values()[1:]

def get_all_remnants_from_sheet():
    client = get_sheet_client()
    if not client:
        return []
    return client.open_by_key(SPREADSHEET_ID).get_worksheet(0).get_all_values()[1:]
