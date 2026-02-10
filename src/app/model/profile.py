from . import db

class Profile(db.Model):
    __tablename__ = 'profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=True) # Name of the place eg London
    lattitude = db.Column(db.String(100), nullable=True)
    longitude = db.Column(db.String(100), nullable=True)
    class_size = db.Column(db.Integer, nullable=True)
    availability = db.Column(db.JSON, nullable=True)  # Store as JSON array
    interests = db.Column(db.JSON, nullable=True)  # Store as JSON array
    
    # Relationships
    sent_relations = db.relationship('Relation', foreign_keys='Relation.from_profile_id', 
                                     backref='from_profile', lazy='dynamic', cascade='all, delete-orphan')
    received_relations = db.relationship('Relation', foreign_keys='Relation.to_profile_id',
                                         backref='to_profile', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Profile {self.name}>'