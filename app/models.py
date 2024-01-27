# python imports
import uuid
import time
from datetime import datetime

# local imports
from app import db


# timestamp to be inherited by other class models
class TimestampMixin(object):
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def format_date(self):
        return self.created_at.strftime("%d %B, %Y %I:%M")


# db helper functions
class DatabaseHelperMixin(object):
    def update(self):
        db.session.commit()

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class Transactions(db.Model, TimestampMixin, DatabaseHelperMixin):
    __tablename__ = "transaction"

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default="pending")
    uid = db.Column(db.String(200), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    reg_no = db.Column(db.String(20), nullable=False)
    part = db.Column(db.String(10), nullable=False)
    fee_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    donation = db.Column(db.Boolean, default=False)
    tx_ref = db.Column(db.String(100), nullable=False)
    flw_tx_id = db.Column(db.String(100))
    flw_tx_ref = db.Column(db.String(100))

    def __init__(self, name, reg_no, part, fee_type, amount, donation) -> None:
        super().__init__()
        self.name = name
        self.reg_no = reg_no
        self.part = part
        self.fee_type = fee_type
        self.amount = amount
        self.donation = donation
        self.uid = uuid.uuid4().hex
        self.tx_ref = (
            f"{self.part.lower()}-{self.reg_no}-{str(time.time()).split('.')[0]}"
            if not self.donation
            else f"dont-{str(time.time()).split('.')[0]}"
        )
