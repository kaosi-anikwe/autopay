# python imports
import os
import json
import traceback
from datetime import datetime

# installed imports
import requests
from dotenv import load_dotenv
from flask import Blueprint, render_template, request, jsonify, redirect, url_for

# local imports
from app import logger, csrf
from app.models import Transactions
from .functions import find_and_replace, add_record, get_data_from_worksheet

main = Blueprint("main", __name__)

load_dotenv()

RAVE_PUB_KEY = os.getenv("RAVE_PUBLIC_KEY")
RAVE_SEC_KEY = os.getenv("RAVE_SECRET_KEY")
LOG_DIR = os.getenv("LOG_DIR", "logs")
WEBHOOK_LOG = os.path.join(LOG_DIR, "webhooks")
os.makedirs(WEBHOOK_LOG, exist_ok=True)

# MAIN ROUTES ------------------------
@main.get("/")
def index():
    return render_template("index.html")


@main.get("/names")
def get_names():
    try:
        part = request.args.get("part", "Soprano")
        logger.info(f"Getting names for {part}")

        names = get_data_from_worksheet(part)

        return jsonify(names=names)
    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify(message="Failed to get names", error=str(e)), 500


@main.post("/tx_ref")
def get_tx_ref():
    try:
        logger.info(f"Generating tx_ref")
        data = request.get_json()
        part = data.get("part")
        name = data.get("name")
        amount = int(data.get("amount"))
        fee_type = data.get("fee_type", "fusion-cantus")
        donation = bool(data.get("donation", False))
        if not part or not name or not amount:
            return jsonify(error="Specify name and part"), 400

        names = get_data_from_worksheet(part)
        reg_no = [info[1] for info in names if info[0] == name][0]

        transaction = Transactions(
            name=name,
            reg_no=reg_no,
            part=part,
            fee_type=fee_type,
            amount=amount,
            donation=donation,
        )
        transaction.insert()
        logger.info(f"TX_REF: {transaction.tx_ref}")
        return jsonify(tx_ref=transaction.tx_ref)
    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify(message="Error getting tx_ref", error=str(e)), 500


# ADMIN ROUTES ---------------------
@main.get("/admin")
def admin():
    return render_template("admin.html")


@main.post("/add-name")
def add_name():
    try:
        form = request.form
        logger.info(f"ADDING NAME WITH DATA: {form}")
        name = form.get("name")
        fee_type = form.get("fee_type")
        part = form.get("part")
        reg_no = form.get("reg_no")
        data = {
            "Name": name.upper(),
            "Reg Number": reg_no,
            "Paid": 0,
        }
        if add_record(data, part):
            return jsonify(success=True)
        raise Exception("Failed to add record")
    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify(error=str(e)), 500


@main.post("/add-payment")
def add_payment():
    try:
        data = request.get_json()
        logger.info(f"ADDING PAYMENT WITH DATA: {data}")
        part = data.get("part")
        name = data.get("name")
        amount = int(data.get("amount"))
        fee_type = data.get("fee_type")
        reg_no = data.get("reg_no")
        donation = bool(data.get("donation"))

        transaction = Transactions(
            name=name,
            reg_no=reg_no,
            part=part,
            fee_type=fee_type,
            amount=amount,
            donation=donation,
        )
        transaction.insert()
        logger.info(f"TX_REF: {transaction.tx_ref}")
        # update speadsheet
        if not donation:
            find_and_replace(
                sheetname=part,
                identify_col="Reg Number",
                identify_value=reg_no,
                column_name="Paid",
                new_value=amount
            )
        else:
            donor_data = {
                "Name": name,
                "Paid": amount
            }
            add_record(donor_data, "Donations", donation=True)
        return jsonify(success=True)
    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify(error=str(e)), 500


# PAYMENT ROUTES -------------------
@main.post("/payment-webhook")
@csrf.exempt
def payment_webhook():
    if request.headers.get("verif-hash") == RAVE_SEC_KEY:
        try:
            payload = request.get_json()

            # create directory for each day
            directory = os.path.join(
                WEBHOOK_LOG, datetime.utcnow().strftime("%d-%m-%Y")
            )
            os.makedirs(directory, exist_ok=True)
            log_file = os.path.join(
                directory, f"{datetime.utcnow().strftime('%H:%M:%S')}.json"
            )
            with open(log_file, "w") as file:
                json.dump(payload, file)

            # get transaction details from payload
            status = payload["data"]["status"]
            tx_ref = payload["data"]["tx_ref"]
            flw_tx_id = payload["data"]["id"]
            flw_tx_ref = payload["data"]["flw_ref"]
            reg_no = str(tx_ref).split("-")[1]

            # get transaction details from database
            tx = Transactions.query.filter(
                Transactions.tx_ref == tx_ref,
                Transactions.status == "pending",
            ).one_or_none()
            if tx:  # transaction found
                # get transaction status
                if status == "successful":
                    verify_url = f"https://api.flutterwave.com/v3/transactions/{int(flw_tx_id)}/verify"
                    try:
                        # verify transaction
                        response = requests.get(
                            verify_url,
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {RAVE_SEC_KEY}",
                            },
                        )
                        if response.status_code == 200:
                            data = response.json()
                            if data["status"] == "success":
                                # update record as successful
                                if (
                                    tx.status != "completed"
                                ):  # transaction was pending
                                    tx.status = "completed"
                                    tx.flw_tx_id = flw_tx_id
                                    tx.flw_tx_ref = flw_tx_ref
                                    tx.update()
                                    # update spreadsheet
                                    part = tx_ref.split("-")[0]
                                    part = str(part).capitalize() if "dont" not in part.lower() else "Donation"
                                    if not tx.donation:
                                        find_and_replace(
                                            sheetname=part,
                                            identify_col="Reg Number",
                                            identify_value=reg_no,
                                            column_name="Paid",
                                            new_value=tx.amount
                                        )
                                    else:
                                        donor_data = {
                                            "Name": tx.name,
                                            "Paid": tx.amount
                                        }
                                        add_record(donor_data, "Donations", donation=True)
                                elif tx.status == "completed":
                                    logger.info(
                                        f"TX #{tx.flw_tx_id} ALREADY VERIFIED"
                                    )

                                return jsonify({"success": True}), 200
                            else:
                                tx.status = data["status"]
                                tx.update()
                                return jsonify({"success": False}), 417
                        else:
                            # update record as failed
                            tx.status = "failed"
                            tx.update()
                            return jsonify({"success": False}), 417
                    except:
                        logger.error(traceback.format_exc())
                        # update record as error
                        tx.status = "error"
                        tx.update()
                        return jsonify({"success": False}), 500
                else:
                    tx.status = status
                    tx.update()
                    return jsonify({"success": False}), 417
            else:
                return jsonify({"success": False}), 404
        except:
            logger.error(traceback.format_exc())
            # update record as error
            tx.status = "error"
            tx.update()
            return jsonify({"success": False}), 500
    else:
        return jsonify({"success": False}), 401


@main.get("/payment-callback")
def payment_callback():
    if request.headers.get("verif-hash") == RAVE_SEC_KEY:
        try:
            payload = request.args
            message = "That didn't really work out 😕"
            link_mssg = "Try again?"

            # create directory for each day
            directory = os.path.join(
                WEBHOOK_LOG, datetime.utcnow().strftime("%d-%m-%Y")
            )
            os.makedirs(directory, exist_ok=True)
            log_file = os.path.join(
                directory, f"{datetime.utcnow().strftime('%H:%M:%S')}.json"
            )
            with open(log_file, "w") as file:
                json.dump(payload, file)

            # get transaction details from payload
            status = payload["status"]
            tx_ref = payload["tx_ref"]
            flw_tx_id = payload["transaction_id"]
            reg_no = str(tx_ref).split("-")[1]

            # get transaction details from database
            tx = Transactions.query.filter(
                Transactions.tx_ref == tx_ref,
                Transactions.status == "pending",
            ).one_or_none()
            if tx:  # transaction found
                # get transaction status
                if status == "successful":
                    verify_url = f"https://api.flutterwave.com/v3/transactions/{int(flw_tx_id)}/verify"
                    try:
                        # verify transaction
                        response = requests.get(
                            verify_url,
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {RAVE_SEC_KEY}",
                            },
                        )
                        if response.status_code == 200:
                            data = response.json()
                            if data["status"] == "success":
                                # update record as successful
                                if (
                                    tx.status != "completed"
                                ):  # transaction was pending
                                    tx.status = "completed"
                                    flw_tx_ref = data["data"]["flw_ref"]
                                    tx.flw_tx_id = flw_tx_id
                                    tx.flw_tx_ref = flw_tx_ref
                                    tx.update()
                                    # update spreadsheet
                                    part = tx_ref.split("-")[0]
                                    part = str(part).capitalize()
                                    if not tx.donation:
                                        find_and_replace(
                                            sheetname=part,
                                            identify_col="Reg Number",
                                            identify_value=reg_no,
                                            column_name="Paid",
                                            new_value=tx.amount
                                        )
                                    else:
                                        donor_data = {
                                            "Name": tx.name,
                                            "Paid": tx.amount
                                        }
                                        add_record(donor_data, "Donations", donation=True)

                                elif tx.status == "completed":
                                    logger.info(
                                        f"TX #{tx.flw_tx_id} ALREADY VERIFIED"
                                    )
                                message = "Thank you for completing the payment ❤️✨" if not tx.donation else "Thank you for donating ❤️✨"
                                link_mssg = "Pay again?"
                                return redirect(url_for("main.thanks", message=message, link_mssg=link_mssg))
                            else:
                                tx.status = data["status"]
                                tx.update()
                                return redirect(url_for("main.thanks", message=message, link_mssg=link_mssg))
                        else:
                            # update record as failed
                            tx.status = "failed"
                            tx.update()
                            return redirect(url_for("main.thanks", message=message, link_mssg=link_mssg))
                    except:
                        logger.error(traceback.format_exc())
                        # update record as error
                        tx.status = "error"
                        tx.update()
                        return redirect(url_for("main.thanks", message=message, link_mssg=link_mssg))
                else:
                    tx.status = status
                    tx.update()
                    return redirect(url_for("main.thanks", message=message, link_mssg=link_mssg))
            else:
                return redirect(url_for("main.thanks", message=message, link_mssg=link_mssg))

        except:
            logger.error(traceback.format_exc())
            # update record as error
            tx.status = "error"
            tx.update()
            return redirect(url_for("main.thanks", message=message, link_mssg=link_mssg))
    else:
        return redirect(url_for("main.thanks", message=message, link_mssg=link_mssg))



@main.get("/thanks")
def thanks(message, link_mssg):
    return render_template("thanks.html", message=message, link_mssg=link_mssg)
