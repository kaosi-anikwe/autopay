# python imports
import traceback

# local imports
from app import logger, csrf
from app.models import Transactions
from .functions import find_and_replace, update_spreadsheet
from flask import Blueprint, render_template, request, jsonify

main = Blueprint("main", __name__)


# MAIN ROUTES ------------------------
@main.get("/")
def index():
    return render_template("index.html")


@main.get("/names")
def get_names():
    try:
        part = request.args.get("part", "Soprano")
        logger.info(f"Getting names for {part}")

        # TODO: get names from spreadsheet

        names = ["JAMES", "IFEANYI", "TAMMY", "CHICHETA", "EDWARD"]
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
        amount = float(data.get("amount"))
        fee_type = data.get("fee_type", "fusion-cantus")
        donatation = bool(data.get("donation", False))
        if not part or not name or not amount:
            return jsonify(error="Specify name and part"), 400

        # TODO: get reg_no with name

        transaction = Transactions(
            name=name,
            reg_no="2020/241781",
            part=part,
            fee_type=fee_type,
            amount=amount,
            donatation=donatation,
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
    return "200"


@main.post("/add-payment")
def add_payment():
    return "200"


# PAYMENT ROUTES -------------------
@main.post("/payment-webhook")
@csrf.exempt
def payment_webhook():
    pass


@main.get("/thanks")
def payment_callback():
    return render_template("thanks.html")
