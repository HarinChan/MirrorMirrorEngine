from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from model.profile import Profile
from model.account import Account
from model.post import Post
from model.relation import Relation

from router.profile import *
from router.account import *
from router.post import *
from router.relation import *

# app is for /router
# db is for /model


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
app.secret_key = 'your_secret_key'  # Change this to something secure!

db = SQLAlchemy(app)
with app.app_context():
    db.create_all()  # Create database tables

app.run(debug=True)
