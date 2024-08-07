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


class Members(db.Model, TimestampMixin, DatabaseHelperMixin):
    __tablename__ = "member"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    part = db.Column(db.String(10), nullable=False)
    phone_no = db.Column(db.String(20), unique=True)

    def __init__(self, name: str, part: str, phone_no: str) -> None:
        self.name = name
        self.part = part
        self.phone_no = phone_no

    def transactions(self):
        return Transactions.query.filter(
            Transactions.member_id == self.id, Transactions.status == "completed"
        ).all()

    def amount(self):
        return sum(
            [
                tx.amount
                for tx in Transactions.query.filter(
                    Transactions.member_id == self.id,
                    Transactions.status == "completed",
                ).all()
            ]
        )


class Transactions(db.Model, TimestampMixin, DatabaseHelperMixin):
    __tablename__ = "transaction"

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default="pending")
    uid = db.Column(db.String(200), unique=True, nullable=False)
    part = db.Column(db.String(10))
    fee_type = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    donation = db.Column(db.Boolean, default=False)
    tx_ref = db.Column(db.String(100), nullable=False)
    flw_tx_id = db.Column(db.String(100))
    flw_tx_ref = db.Column(db.String(100))
    member_id = db.Column(db.ForeignKey("member.id"))

    def __init__(
        self, part, fee_type, amount, tx_ref, member_id=None, donation=False
    ) -> None:
        self.part = part
        self.fee_type = fee_type
        self.amount = amount
        self.uid = uuid.uuid4().hex
        self.tx_ref = tx_ref
        self.member_id = member_id
        self.donation = donation

    @staticmethod
    def get_tx_ref(part: str):
        return f"{part.lower()}-{str(time.time()).split('.')[0]}"
