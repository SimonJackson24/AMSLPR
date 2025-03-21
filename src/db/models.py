
# AMSLPR - Automate Systems License Plate Recognition
# Copyright (c) 2025 Automate Systems. All rights reserved.
#
# This software is proprietary and confidential.
# Unauthorized use, reproduction, or distribution is prohibited.

"""Database models for AMSLPR."""
import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from src.db.manager import Base

class User(Base):
    """User model for authentication."""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_login = Column(DateTime)

class Vehicle(Base):
    """Vehicle model for license plate management."""
    __tablename__ = 'vehicles'
    
    id = Column(Integer, primary_key=True)
    plate_number = Column(String(20), unique=True, nullable=False)
    description = Column(String(200))
    is_authorized = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    access_logs = relationship('AccessLog', back_populates='vehicle')
    parking_sessions = relationship('ParkingSession', back_populates='vehicle')

class AccessLog(Base):
    """Access log model for vehicle entry/exit tracking."""
    __tablename__ = 'access_logs'
    
    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey('vehicles.id'))
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    event_type = Column(String(10))  # 'entry' or 'exit'
    confidence = Column(Float)
    image_path = Column(String(200))
    
    # Relationships
    vehicle = relationship('Vehicle', back_populates='access_logs')

class ApiKey(Base):
    """API key model for REST API authentication."""
    __tablename__ = 'api_keys'
    
    id = Column(Integer, primary_key=True)
    key = Column(String(64), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey('users.id'))

class ParkingSession(Base):
    """Parking session model for parking management."""
    __tablename__ = 'parking_sessions'
    
    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey('vehicles.id'))
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime)
    duration = Column(Integer)  # Duration in seconds
    fee = Column(Float)  # Parking fee if applicable
    paid = Column(Boolean, default=False)
    payment_time = Column(DateTime)
    
    # Relationships
    vehicle = relationship('Vehicle', back_populates='parking_sessions')
