from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

# 1. Crea la instancia de SQLAlchemy aquí.
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(50), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    full_name = db.Column(db.String(100), nullable=False)
    occupation = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    vehicles = db.relationship('Vehicle', backref='user', lazy=True, cascade='all, delete-orphan')
    access_logs = db.relationship('AccessLog', backref='user', lazy=True)

class Vehicle(db.Model):
    __tablename__ = 'vehicles'
    
    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    __table_args__ = (
        db.Index('idx_plate_number', 'plate_number'),
    )

class AccessLog(db.Model):
    __tablename__ = 'access_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    authorized = db.Column(db.Boolean, nullable=False)
    confidence = db.Column(db.Float, default=0.0)
    image_path = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    __table_args__ = (
        db.Index('idx_timestamp', 'timestamp'),
        db.Index('idx_plate_authorized', 'plate_number', 'authorized'),
    )

class Alert(db.Model):
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    access_log_id = db.Column(db.Integer, db.ForeignKey('access_logs.id'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    acknowledged_at = db.Column(db.DateTime, nullable=True)
    
    access_log = db.relationship('AccessLog', backref='alerts')
    acknowledged_by_user = db.relationship('User', foreign_keys=[acknowledged_by])