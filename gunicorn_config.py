import os
from dotenv import load_dotenv

load_dotenv()

# gunicorn config
bind = "unix:app.sock"
workers = 1
accesslog = os.path.join(os.getenv("BASE_DIR"), "logs", "run.log")
errorlog = os.path.join(os.getenv("BASE_DIR"), "logs", "run.log")
