# python imports
import os
import json
import string
import tempfile

# installed imports
import gspread
import pandas as pd
from dotenv import load_dotenv
from werkzeug.datastructures import FileStorage
from oauth2client.service_account import ServiceAccountCredentials

# local imports
from app import logger
from app.models import Members

load_dotenv()

ACCEPTED_SHEETNAMES = ["Soprano", "Alto", "Tenor", "Bass", "Donations"]

spreadsheet_id = os.getenv("SPREADSHEET_ID")
google_credentials_file = json.loads(os.getenv("CREDENTIALS_FILE"), strict=False)

# Set up the scope for accessing Google Sheets
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
# Authenticate with Google Sheets
creds = ServiceAccountCredentials.from_json_keyfile_dict(google_credentials_file, scope)
gclient = gspread.authorize(creds)

# get sheet IDs
with open("sheets.json") as sheets_data:
    sheets = json.load(sheets_data)["sheets"]


def get_last_column_letter(sheet):
    # Get all values in the first row (headers)
    header_row = sheet.row_values(1)

    # Find the index of the last non-empty cell in the first row
    last_non_empty_index = (
        len(header_row)
        - header_row[::-1].index(next(filter(None, reversed(header_row))))
        - 1
    )

    # Convert the index to a column letter
    last_column_letter = string.ascii_uppercase[last_non_empty_index]

    return last_column_letter


def add_record(
    data: dict,
    sheetname: str,
    fee_type: str,
    check_column: str = "Phone No",
    sort_column: str = "Name",
    donation=False,
):
    spreadsheet = gclient.open_by_key(sheets.get(fee_type))
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

    if not donation:
        # Get all values in the specified check column
        check_column_values = worksheet.col_values(header.index(check_column) + 1)

        # Check if the specified value in the input data is already in the check column
        if data[check_column] in check_column_values:
            logger.info(
                f"Record with '{check_column}' equal to '{data[check_column]}' already exists."
            )
            return False

    # Append the row to the worksheet
    values = list(data.values())
    worksheet.append_row(values)

    # Sort the rows alphabetically based on the specified sort column
    sort_column_index = header.index(sort_column) + 1
    last_column_letter = get_last_column_letter(worksheet)
    last_row_index = worksheet.row_count
    worksheet.sort(
        (sort_column_index, "asc"), range=f"A2:{last_column_letter}{last_row_index}"
    )

    return True


def find_and_replace(
    fee_type: str,
    identify_value,
    new_value,
    identify_col: str,
    column_name: str,
    sheetname: str,
    replace = True,
):
    spreadsheet = gclient.open_by_key(sheets.get(fee_type))
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
    total_value = int(new_value) + int(current_value) if not replace else int(new_value)
    worksheet.update_cell(row_index, column_index, total_value)
    return total_value


def get_data_from_worksheet(sheetname: str, fee_type: str):
    spreadsheet = gclient.open_by_key(sheets.get(fee_type))
    if sheetname not in [worksheet.title for worksheet in spreadsheet.worksheets()]:
        worksheet = spreadsheet.add_worksheet(sheetname, rows=100, cols=20)
    else:
        worksheet = spreadsheet.worksheet(sheetname)

    data_range = worksheet.get_all_values()[1:]  # Exclude the header row
    data = [(row[0], row[1]) for row in data_range]

    return data


def file_upload(namefile: FileStorage, fee_type: str):
    logger.info("POPULATING SPREADSHEET WITH UPLOADED FILE")
    logger.info(f"FILE: {namefile}")
    spreadsheet = gclient.open_by_key(sheets.get(fee_type))
    with tempfile.NamedTemporaryFile("w", suffix=".xlsx") as temp_file:
        namefile.save(temp_file.name)
        xls = pd.ExcelFile(temp_file.name, engine="openpyxl")
        for sheetname in xls.sheet_names:
            if sheetname in ACCEPTED_SHEETNAMES:
                df = pd.read_excel(xls, sheetname).fillna(0)
                if sheetname not in [
                    worksheet.title for worksheet in spreadsheet.worksheets()
                ]:
                    worksheet = spreadsheet.add_worksheet(sheetname, rows=100, cols=20)
                else:
                    worksheet = spreadsheet.worksheet(sheetname)
                # clear worksheet and upload new sheet
                worksheet.clear()
                header = df.columns.tolist()
                values = df.values.tolist()
                # add header
                logger.info(f"Updating Header: {header}")
                worksheet.update("A1", [header])
                # add values
                logger.info(f"Adding values...")
                worksheet.update("A2", values)
                logger.info("Done adding values")
                # Sort the rows alphabetically based on the specified sort column
                sort_column_index = header.index("Name") + 1
                last_column_letter = get_last_column_letter(worksheet)
                last_row_index = worksheet.row_count
                worksheet.sort(
                    (sort_column_index, "asc"),
                    range=f"A2:{last_column_letter}{last_row_index}",
                )


def populate_db(force=False):
    if not force:
        check = len(Members.query.all())
        force = True if not check else False
        if not force:
            logger.info(f"db already populated")
    if force:
        # purge all records
        logger.info("Purging all member records")
        from app import db
        import csv

        db.session.query(Members).delete()
        db.session.commit()

        # add new records
        logger.info("Adding new member records")

        with open("db.tsv", "r") as file:
            reader = csv.reader(file, delimiter="\t")
            next(reader)  # skip the header
            for row in reader:
                member = Members(
                    name=row[0].upper(),
                    phone_no=row[1],
                    part=row[2].lower(),
                )
                member.insert()
                logger.info(f"Added {row[2]} member with ID: {member.id}")
        return populate_sheet()


def populate_sheet(fee_type="fusion-cantus"):
    logger.info("POPULATING SPREADSHEET WITH DATABASE RECORDS")
    spreadsheet = gclient.open_by_key(sheets.get(fee_type))
    parts = ["Soprano", "Alto", "Tenor", "Bass"]
    header = ["Name", "Phone No", "Paid"]
    for part in parts:
        members = Members.query.filter(Members.part == part.lower()).all()
        if part not in [worksheet.title for worksheet in spreadsheet.worksheets()]:
            worksheet = spreadsheet.add_worksheet(part, rows=100, cols=20)
        else:
            worksheet = spreadsheet.worksheet(part)
        # clear worksheet and upload new record
        worksheet.clear()
        values = [[member.name, member.phone_no, member.amount()] for member in members]
        # add header
        logger.info(f"Updating Header: {header}")
        worksheet.update("A1", [header])
        # add values
        logger.info("Adding values")
        worksheet.update("A2", values)
        logger.info("Done adding values")
        # Sort the rows alphabetically based on the specified sort column
        sort_column_index = header.index("Name") + 1
        last_column_letter = get_last_column_letter(worksheet)
        last_row_index = worksheet.row_count
        worksheet.sort(
            (sort_column_index, "asc"),
            range=f"A2:{last_column_letter}{last_row_index}",
        )
