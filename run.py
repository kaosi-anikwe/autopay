import os
from dotenv import load_dotenv
from app import create_app, db
from app.main.functions import populate_db

load_dotenv()

app = create_app()

with app.app_context():
    db.create_all()
    populate_db()

if __name__ == "__main__":
    app.run(debug=True, host=os.getenv("SERVER_NAME"), port=4000)
