
# Load environment variables from .env file before importing main
from dotenv import load_dotenv
load_dotenv()
from main import application, db

with application.app_context():
    db.create_all()
    print("Database tables created successfully!")