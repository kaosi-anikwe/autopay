# python imports
from datetime import datetime

# local imports
from app import db


# timestamp to be inherited by other class models
class TimestampMixin(object):
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def format_date(self):
        return self.created_at.strftime("%d %B, %Y %I:%M")
