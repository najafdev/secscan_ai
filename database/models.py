#!/usr/bin/env python3
# SecScan AI core module
"""
Database models for SecScan AI
SQLAlchemy ORM models for data persistence
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

Base = declarative_base()

class PentestSession(Base):
    __tablename__ = 'pentest_sessions'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    target = Column(String, nullable=False)
    scope = Column(Text, nullable=False)
    status = Column(String, default='running')  # running, completed, failed, paused
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    created_by = Column(String, nullable=False)
    auth_key_hash = Column(String, nullable=False)
    assessment_type = Column(String, default='black-box')
    
    # Relationships
    vulnerabilities = relationship("Vulnerability", back_populates="session")
    phase_results = relationship("PhaseResult", back_populates="session")
    
class Vulnerability(Base):
    __tablename__ = 'vulnerabilities'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey('pentest_sessions.id'), nullable=False)
    phase = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # critical, high, medium, low, info
    cvss_score = Column(Float)
    cvss_vector = Column(String)
    title = Column(String, nullable=False)
    description = Column(Text)
    proof_of_concept = Column(Text)
    remediation = Column(Text)
    references = Column(JSON)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default='open')  # open, fixed, false_positive, risk_accepted
    ticket_id = Column(String)  # For JIRA integration
    
    # Relationships
    session = relationship("PentestSession", back_populates="vulnerabilities")
    attack_chains = relationship("AttackChain", back_populates="vulnerability")

class PhaseResult(Base):
    __tablename__ = 'phase_results'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey('pentest_sessions.id'), nullable=False)
    phase_name = Column(String, nullable=False)
    phase_number = Column(Integer, nullable=False)
    status = Column(String, default='running')  # running, completed, failed, skipped
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    results = Column(JSON)
    ai_analysis = Column(Text)
    tools_used = Column(JSON)
    execution_time = Column(Float)  # seconds
    
    # Relationships
    session = relationship("PentestSession", back_populates="phase_results")

class AttackChain(Base):
    __tablename__ = 'attack_chains'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, nullable=False)
    vulnerability_id = Column(String, ForeignKey('vulnerabilities.id'), nullable=False)
    chain_sequence = Column(Integer, nullable=False)
    exploit_path = Column(JSON, nullable=False)
    risk_score = Column(Float, nullable=False)
    impact_description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    vulnerability = relationship("Vulnerability", back_populates="attack_chains")

class User(Base):
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default='analyst')  # admin, senior_analyst, analyst, viewer
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String)
    details = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String)
    user_agent = Column(String)

class Configuration(Base):
    __tablename__ = 'configurations'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String, unique=True, nullable=False)
    value = Column(JSON, nullable=False)
    description = Column(Text)
    category = Column(String, default='general')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class AIContext(Base):
    __tablename__ = 'ai_contexts'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, nullable=False)
    context_type = Column(String, nullable=False)  # session, target, vulnerability
    context_data = Column(JSON, nullable=False)
    confidence_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
