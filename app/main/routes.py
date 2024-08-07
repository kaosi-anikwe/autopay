# python imports
import os
import json
import time
import traceback
from datetime import datetime

# installed imports
import requests
from dotenv import load_dotenv
from flask import Blueprint, render_template, request, jsonify, redirect, url_for

# local imports
from app import logger, csrf
from app.models import Transactions, Members
from .functions import (
    find_and_replace,
    add_record,
    file_upload,
)

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
        part = request.args.get("part")
        fee_type = request.args.get("fee_type")
        logger.info(f"Getting names for {fee_type} {part}")

        names = [
            (member.name, member.phone_no)
            for member in Members.query.filter(Members.part == part).all()
        ]

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

        tx_ref = Transactions.get_tx_ref(part)
        member = Members.query.filter(Members.name == name).one_or_404()

        logger.info(f"TX_REF: {tx_ref}")
        return jsonify(tx_ref=tx_ref, member_id=member.id)
    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify(message="Error getting tx_ref", error=str(e)), 500


@main.get("/thanks")
def thanks():
    message = request.args.get("message")
    link_mssg = request.args.get("link_mssg")
    fee_type = request.args.get("fee_type")
    title = "Thank you ❤️✨" if "thank" in message.lower() else "Sorry 😕"
    return render_template(
        "thanks.html",
        message=message,
        link_mssg=link_mssg,
        title=title,
        page_style=fee_type,
    )


# ADMIN ROUTES ---------------------
@main.get("/admin")
def admin():
    return render_template("admin.html", title="Admin Portal")


@main.post("/add-name")
def add_name():
    try:
        form = request.form
        logger.info(f"ADDING NAME WITH DATA: {form}")
        name_file = request.files.get("name-file")
        fee_type = form.get("fee_type")
        if name_file:
            file_upload(name_file, fee_type)
        name = form.get("name")
        part = form.get("part")
        phone_no = form.get("phone_no")
        new_member = Members(name.upper(), part, phone_no)
        new_member.insert()
        data = {
            "Name": name.upper(),
            "Phone No": phone_no,
            "Paid": 0,
        }
        if add_record(data, sheetname=part, fee_type=fee_type):
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
        name = data.get("name")
        amount = int(data.get("amount"))
        fee_type = data.get("fee_type")
        phone_no = data.get("phone_no")
        donation = bool(data.get("donation", False))
        part = data.get("part") if not donation else "dont"
        tx_ref = Transactions.get_tx_ref(part)
        member = Members.query.filter(Members.phone_no == phone_no).one_or_404()

        # create transaction record
        transaction = (
            Transactions(
                member_id=member.id,
                part=part,
                fee_type=fee_type,
                amount=amount,
                tx_ref=tx_ref,
            )
            if not donation
            else Transactions(
                part=part,
                fee_type=fee_type,
                amount=amount,
                tx_ref=tx_ref,
                donation=donation,
            )
        )
        transaction.status = "completed"
        transaction.insert()
        logger.info(f"TX_REF: {transaction.tx_ref}")
        # update speadsheet
        if not donation:
            find_and_replace(
                fee_type=fee_type,
                sheetname=part,
                identify_col="Phone No",
                identify_value=phone_no,
                column_name="Paid",
                new_value=amount,
            )
        else:
            donor_data = {"Name": name, "Paid": amount}
            add_record(
                donor_data, sheetname="Donations", fee_type=fee_type, donation=True
            )
        return jsonify(success=True)
    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify(error=str(e)), 500


# PAYMENT ROUTES -------------------
@main.post("/payment-webhook")
@csrf.exempt
def payment_webhook():
    time.sleep(10)  # delay to avoid concurrent request with callback
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
            status = payload["data"].get("status")
            tx_ref = payload["data"].get("tx_ref")
            flw_tx_id = payload["data"].get("id")

            # get transaction details from database
            tx = Transactions.query.filter(
                Transactions.tx_ref == tx_ref,
            ).one_or_none()
            if not tx:  # new transaciton
                # get transaction status
                if status == "completed" or status == "successful":
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
                                # create transaction
                                flw_tx_ref = data["data"]["flw_ref"]
                                name = data["data"]["customer"]["name"]
                                amount = data["data"]["amount"]
                                fee_type = data["data"]["meta"]["fee_type"]
                                part = data["data"]["meta"]["part"]
                                member_id = int(data["data"]["meta"]["member_id"])
                                member = Members.query.get(member_id)
                                tx = Transactions(
                                    member_id=member.id,
                                    part=part,
                                    fee_type=fee_type,
                                    amount=amount,
                                    tx_ref=tx_ref,
                                )
                                tx.insert()
                                # update record as successful
                                tx.status = "completed"
                                tx.flw_tx_id = flw_tx_id
                                tx.flw_tx_ref = flw_tx_ref
                                tx.update()
                                # update spreadsheet
                                logger.info(
                                    f"UPDATING BALANCE FOR {name}. ADDING {amount}"
                                )
                                find_and_replace(
                                    fee_type=fee_type,
                                    sheetname=part,
                                    identify_col="Phone No",
                                    identify_value=member.phone_no,
                                    column_name="Paid",
                                    new_value=member.amount(),
                                )
                                return jsonify({"success": True}), 200
                            else:
                                tx.status = data["status"]
                                tx.update()
                                return jsonify({"success": False}), 417
                        else:
                            return jsonify({"success": False}), 417
                    except:
                        logger.error(traceback.format_exc())
                        return jsonify({"success": False}), 500
                else:
                    return jsonify({"success": False}), 417
            else:
                # transaction already exists
                if tx.status == "completed" or tx.status == "successful":
                    logger.info(f"PAYMENT ALREADY VERIFIED: {tx_ref}")
                    return jsonify({"success": True}), 200
                return jsonify({"success": False}), 500
        except:
            logger.error(traceback.format_exc())
            return jsonify({"success": False}), 500
    else:
        return jsonify({"success": False}), 401


@main.get("/payment-callback")
def payment_callback():
    message = "<h3>That didn't really work out 😕</h3>"
    link_mssg = "Try again?"
    try:
        payload = request.args
        # get transaction details from payload
        status = payload.get("status")
        tx_ref = payload.get("tx_ref")
        flw_tx_id = payload.get("transaction_id")

        # get transaction details from database
        tx = Transactions.query.filter(
            Transactions.tx_ref == tx_ref,
        ).one_or_none()
        if not tx:  # new transaction
            # get transaction status
            if status == "completed" or status == "successful":
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
                            # create transaction
                            flw_tx_ref = data["data"]["flw_ref"]
                            name = data["data"]["customer"]["name"]
                            amount = data["data"]["amount"]
                            fee_type = data["data"]["meta"]["fee_type"]
                            part = data["data"]["meta"]["part"]
                            member_id = int(data["data"]["meta"]["member_id"])
                            member = Members.query.get(member_id)
                            tx = Transactions(
                                member_id=member.id,
                                part=part,
                                fee_type=fee_type,
                                amount=amount,
                                tx_ref=tx_ref,
                            )
                            tx.insert()
                            # update record as successful
                            tx.status = "completed"
                            tx.flw_tx_id = flw_tx_id
                            tx.flw_tx_ref = flw_tx_ref
                            tx.update()
                            # update spreadsheet
                            logger.info(f"UPDATING BALANCE FOR {name}. ADDING {amount}")
                            total = find_and_replace(
                                fee_type=fee_type,
                                sheetname=part,
                                identify_col="Phone No",
                                identify_value=member.phone_no,
                                column_name="Paid",
                                new_value=member.amount(),
                            )

                            message = f"<h3>Thank you for completing the payment ❤️✨</h3><p class='h6 mb-2'>You have paid ₦{member.amount():.2f} in total.</p>"
                            link_mssg = "Pay again?"
                            return redirect(
                                url_for(
                                    "main.thanks",
                                    message=message,
                                    link_mssg=link_mssg,
                                    fee_type=fee_type,
                                )
                                + "#main-body"
                            )
                        else:
                            tx.status = data["status"]
                            tx.update()
                            return redirect(
                                url_for(
                                    "main.thanks",
                                    message=message,
                                    link_mssg=link_mssg,
                                )
                                + "#main-body"
                            )
                    else:
                        return redirect(
                            url_for("main.thanks", message=message, link_mssg=link_mssg)
                            + "#main-body"
                        )
                except:
                    logger.error(traceback.format_exc())
                    return redirect(
                        url_for("main.thanks", message=message, link_mssg=link_mssg)
                        + "#main-body"
                    )
            else:
                return redirect(
                    url_for("main.thanks", message=message, link_mssg=link_mssg)
                    + "#main-body"
                )
        else:
            # transaction already exists
            if tx.status == "completed" or tx.status == "successful":
                logger.info(f"PAYMENT ALREADY VERIFIED: {tx_ref}")
                total = Members.query.get(
                    Transactions.query.filter(Transactions.tx_ref == tx_ref)
                    .one()
                    .member_id
                ).amount()
                message = f"<h3>Thank you for completing the payment ❤️✨</h3><p class='h6 mb-2'>You have paid ₦{total:.2f} in total.</p>"
                link_mssg = "Pay again?"
            return redirect(
                url_for("main.thanks", message=message, link_mssg=link_mssg)
                + "#main-body"
            )
    except:
        logger.error(traceback.format_exc())
        return redirect(
            url_for("main.thanks", message=message, link_mssg=link_mssg) + "#main-body"
        )
