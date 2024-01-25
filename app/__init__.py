import os
import logging
from flask import Flask
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from logging.handlers import RotatingFileHandler

from config import Config

load_dotenv()

db = SQLAlchemy()
csrf = CSRFProtect()

# Logging configuration
log_dir = os.getenv("LOG_DIR", "logs")
os.makedirs(log_dir, exist_ok=True)
log_filename = os.path.join(log_dir, "run.log")
log_max_size = 1 * 1024 * 1024  # 1 MB

# Create a logger
logger = logging.getLogger("autopay")
logger.setLevel(logging.DEBUG)

# Create a file handler with log rotation
handler = RotatingFileHandler(log_filename, maxBytes=log_max_size, backupCount=5)

# Create a formatter
formatter = logging.Formatter("%(asctime)s [%(levelname)s] - %(message)s")
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)


def create_app(config=Config):
    app = Flask(__name__)

    app.config.from_object(config)

    db.init_app(app)
    csrf.init_app(app)

    from .main.routes import main

    app.register_blueprint(main)

    return app