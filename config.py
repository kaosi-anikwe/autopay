import os
from dotenv import load_dotenv

load_dotenv()

class Config(object):
    # key for CSF
    SECRET_KEY = os.environ.get("SECRET_KEY")
    # sqlalchemy .db location (for sqlite)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    # sqlalchemy track modifications in sqlalchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECURITY_PASSWORD_SALT = os.environ.get("SECURITY_PASSWORD_SALT")
    # app
    SERVER_NAME = os.environ.get("SERVER_NAME")
    PREFERRED_URL_SCHEME = "https"
