# python imports
import os

# installed imports
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

# local imports
from . import logger

load_dotenv()

spreadsheet_id = os.getenv("SPREADSHEET_ID")
google_credentials_file = os.getenv("CREDENTIALS_FILE")

# Set up the scope for accessing Google Sheets
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
# Authenticate with Google Sheets
creds = ServiceAccountCredentials.from_json_keyfile_name(google_credentials_file, scope)
client = gspread.authorize(creds)
# get spreadsheet
spreadsheet = client.open_by_key(spreadsheet_id)


def update_spreadsheet(data: dict, sheetname: str, check_column: str, sort_column: str):
    # Get worksheet
    if sheetname not in [worksheet.title for worksheet in spreadsheet.worksheets()]:
        worksheet = spreadsheet.add_worksheet(sheetname, rows=100, cols=20)
    else:
        worksheet = spreadsheet.worksheet(sheetname)

    # Get headers
    header_row = worksheet.row_values(1)
    header = list(data.keys())

    # Update header row if needed
    if header_row != header:
        logger.info(f"Updating header")
        worksheet.update("A1", [header])

    # Get all values in the specified check column
    check_column_values = worksheet.col_values(header.index(check_column) + 1)

    # Check if the specified value in the input data is already in the check column
    if data[check_column] in check_column_values:
        logger.info(f"Record with '{check_column}' equal to '{data[check_column]}' already exists.")
        return False, "duplicate"

    # Append the row to the worksheet
    values = list(data.values())
    worksheet.append_row(values, value_input_option="USER_ENTERED")

    # Sort the rows alphabetically based on the specified sort column
    sort_column_index = header.index(sort_column) + 1
    worksheet.sort(sort_column_index, True)  # Set the second parameter to False for descending order

    return True, "successful."



def find_and_replace(
    identify_value,
    new_value,
    identify_col: str,
    column_name: str,
    sheetname: str,
):
    # Get worksheet
    if sheetname not in [worksheet.title for worksheet in spreadsheet.worksheets()]:
        worksheet = spreadsheet.add_worksheet(sheetname, rows=100, cols=20)
    else:
        worksheet = spreadsheet.worksheet(sheetname)
    # Get headers (assumes headers are in the first row)
    headers = worksheet.row_values(1)

    if column_name not in headers:
        logger.info(f"Column '{column_name}' not found.")
        return
    # Find the index of the specified column
    column_index = headers.index(column_name) + 1
    # Get all values in the specified row identifier column
    identifier_column_values = worksheet.col_values(headers.index(identify_col) + 1)

    if identify_value not in identifier_column_values:
        logger.info(f"Row with '{identify_col}' equal to '{identify_value}' not found.")
        return
    # Find the row index where the row_identifier_value is located
    row_index = identifier_column_values.index(identify_value) + 1

    # Get the current value of the cell
    current_value = worksheet.cell(row_index, column_index).value

    # Replace the value in the specified cell
    return worksheet.update_cell(row_index, column_index, int(new_value) + int(current_value))

