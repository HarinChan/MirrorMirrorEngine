from flask import Flask
from flask_sqlalchemy import SQLAlchemy


# app is for /router
# db is for /model


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
app.secret_key = 'your_secret_key'  # Change this to something secure!

db = SQLAlchemy(app)
with app.app_context():
    db.create_all()  # Create database tables

app.run(debug=True)