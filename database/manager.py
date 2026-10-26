#!/usr/bin/env python3
# SecScan AI core module
"""
Database manager for SecScan AI
Handles database connections, migrations, and operations
"""

import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
from .models import Base, PentestSession, Vulnerability, PhaseResult, User, AuditLog, Configuration, AIContext, AttackChain
from datetime import datetime
from typing import List, Optional, Dict, Any
import hashlib
import json

class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self, database_url: str = None):
        if database_url is None:
            # Default to PostgreSQL, fallback to SQLite for development
            database_url = os.getenv('DATABASE_URL', 'sqlite:///secscan_ai.db')
        
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        self.logger = logging.getLogger(__name__)
        
    def create_tables(self):
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            self.logger.info("Database tables created successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error creating tables: {e}")
            return False
    
    @contextmanager
    def get_session(self):
        """Get database session with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def test_connection(self):
        """Test database connection"""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            self.logger.error(f"Database connection failed: {e}")
            return False
    
    # Session management
    def create_pentest_session(self, target: str, scope: str, created_by: str, auth_key: str, assessment_type: str = "black-box") -> str:
        """Create a new pentest session"""
        with self.get_session() as session:
            # Hash the auth key for security
            auth_key_hash = hashlib.sha256(auth_key.encode()).hexdigest()
            
            pentest_session = PentestSession(
                target=target,
                scope=scope,
                created_by=created_by,
                auth_key_hash=auth_key_hash,
                assessment_type=assessment_type
            )
            
            session.add(pentest_session)
            session.flush()  # Get the ID
            session_id = pentest_session.id
            
        self.log_action(created_by, 'create', 'pentest_session', session_id, 
                      {'target': target, 'scope': scope})
        
        return session_id
    
    def get_pentest_session(self, session_id: str) -> Optional[PentestSession]:
        """Get pentest session by ID"""
        with self.get_session() as session:
            result = session.query(PentestSession).filter(PentestSession.id == session_id).first()
            if result:
                session.expunge(result)
            return result

    def get_recent_sessions(self, limit: int = 50) -> List[PentestSession]:
        """Get recent pentest sessions"""
        with self.get_session() as session:
            results = session.query(PentestSession).order_by(PentestSession.created_at.desc()).limit(limit).all()
            for r in results:
                session.expunge(r)
            return results
    
    def update_session_status(self, session_id: str, status: str, user_id: str):
        """Update session status"""
        old_status = None
        with self.get_session() as session:
            pentest_session = session.query(PentestSession).filter(PentestSession.id == session_id).first()
            if pentest_session:
                old_status = pentest_session.status
                pentest_session.status = status
                if status == 'completed':
                    pentest_session.completed_at = datetime.utcnow()
                
        if old_status is not None:
            self.log_action(user_id, 'update', 'pentest_session', session_id,
                          {'old_status': old_status, 'new_status': status})
    
    # Vulnerability management
    def create_vulnerability(self, session_id: str, phase: str, severity: str, title: str,
                           description: str, cvss_score: float = None, cvss_vector: str = None,
                           proof_of_concept: str = None, remediation: str = None,
                           references: List[str] = None) -> str:
        """Create a new vulnerability"""
        with self.get_session() as session:
            vulnerability = Vulnerability(
                session_id=session_id,
                phase=phase,
                severity=severity,
                title=title,
                description=description,
                cvss_score=cvss_score,
                cvss_vector=cvss_vector,
                proof_of_concept=proof_of_concept,
                remediation=remediation,
                references=references or []
            )
            
            session.add(vulnerability)
            session.flush()
            
            return vulnerability.id
    
    def get_vulnerabilities_by_session(self, session_id: str) -> List[Vulnerability]:
        """Get all vulnerabilities for a session"""
        with self.get_session() as session:
            results = session.query(Vulnerability).filter(Vulnerability.session_id == session_id).all()
            for r in results:
                session.expunge(r)
            return results
    
    def get_vulnerabilities_by_severity(self, session_id: str, severity: str) -> List[Vulnerability]:
        """Get vulnerabilities by severity"""
        with self.get_session() as session:
            results = session.query(Vulnerability).filter(
                Vulnerability.session_id == session_id,
                Vulnerability.severity == severity
            ).all()
            for r in results:
                session.expunge(r)
            return results
    
    # Phase result management
    def create_phase_result(self, session_id: str, phase_name: str, phase_number: int,
                          results: Dict[str, Any], ai_analysis: str = None,
                          tools_used: List[str] = None) -> str:
        """Create a new phase result"""
        with self.get_session() as session:
            phase_result = PhaseResult(
                session_id=session_id,
                phase_name=phase_name,
                phase_number=phase_number,
                results=results,
                ai_analysis=ai_analysis,
                tools_used=tools_used or []
            )
            
            session.add(phase_result)
            session.flush()
            
            return phase_result.id
    
    def update_phase_result(self, result_id: str, status: str, completed_at: datetime = None,
                          results: Dict[str, Any] = None, ai_analysis: str = None, execution_time: float = None):
        """Update phase result"""
        with self.get_session() as session:
            phase_result = session.query(PhaseResult).filter(PhaseResult.id == result_id).first()
            if phase_result:
                phase_result.status = status
                phase_result.completed_at = completed_at or datetime.utcnow()
                if results is not None:
                    phase_result.results = results
                if ai_analysis is not None:
                    phase_result.ai_analysis = ai_analysis
                if execution_time is not None:
                    phase_result.execution_time = execution_time

    def get_phase_results(self, session_id: str) -> List[PhaseResult]:
        """Get all phase results for a session"""
        with self.get_session() as session:
            results = session.query(PhaseResult).filter(
                PhaseResult.session_id == session_id
            ).order_by(PhaseResult.phase_number).all()
            for r in results:
                session.expunge(r)
            return results
    
    # User management
    def create_user(self, username: str, email: str, password_hash: str, role: str = 'analyst') -> str:
        """Create a new user"""
        with self.get_session() as session:
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                role=role
            )
            
            session.add(user)
            session.flush()
            
            return user.id
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        with self.get_session() as session:
            result = session.query(User).filter(User.username == username).first()
            if result:
                session.expunge(result)
            return result
    
    def update_user_login(self, user_id: str):
        """Update user last login time"""
        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.last_login = datetime.utcnow()
    
    # Audit logging
    def log_action(self, user_id: str, action: str, resource_type: str, resource_id: str = None,
                  details: Dict[str, Any] = None, ip_address: str = None, user_agent: str = None):
        """Log user action for audit trail"""
        with self.get_session() as session:
            audit_log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            session.add(audit_log)
    
    def get_audit_logs(self, user_id: str = None, action: str = None, 
                      resource_type: str = None, limit: int = 100) -> List[AuditLog]:
        """Get audit logs with filters"""
        with self.get_session() as session:
            query = session.query(AuditLog)
            
            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            if action:
                query = query.filter(AuditLog.action == action)
            if resource_type:
                query = query.filter(AuditLog.resource_type == resource_type)
                
            results = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
            for r in results:
                session.expunge(r)
            return results
    
    # Configuration management
    def set_configuration(self, key: str, value: Any, description: str = None, category: str = 'general'):
        """Set configuration value"""
        with self.get_session() as session:
            config = session.query(Configuration).filter(Configuration.key == key).first()
            
            if config:
                config.value = value
                config.updated_at = datetime.utcnow()
                if description:
                    config.description = description
            else:
                config = Configuration(
                    key=key,
                    value=value,
                    description=description,
                    category=category
                )
                session.add(config)
    
    def get_configuration(self, key: str, default=None):
        """Get configuration value"""
        with self.get_session() as session:
            config = session.query(Configuration).filter(Configuration.key == key).first()
            return config.value if config else default
    
    # AI Context management
    def save_ai_context(self, session_id: str, context_type: str, context_data: Dict[str, Any],
                       confidence_score: float = None) -> str:
        """Save AI context for future reference"""
        with self.get_session() as session:
            context = AIContext(
                session_id=session_id,
                context_type=context_type,
                context_data=context_data,
                confidence_score=confidence_score
            )
            
            session.add(context)
            session.flush()
            
            return context.id
    
    def get_ai_context(self, session_id: str, context_type: str = None) -> List[AIContext]:
        """Get AI context for session"""
        with self.get_session() as session:
            query = session.query(AIContext).filter(AIContext.session_id == session_id)
            
            if context_type:
                query = query.filter(AIContext.context_type == context_type)
                
            results = query.order_by(AIContext.created_at.desc()).all()
            for r in results:
                session.expunge(r)
            return results
    
    # Attack Chain management
    def create_attack_chain(self, session_id: str, vulnerability_id: str, chain_sequence: int,
                          exploit_path: List[Dict[str, Any]], risk_score: float,
                          impact_description: str = None) -> str:
        """Create attack chain"""
        with self.get_session() as session:
            attack_chain = AttackChain(
                session_id=session_id,
                vulnerability_id=vulnerability_id,
                chain_sequence=chain_sequence,
                exploit_path=exploit_path,
                risk_score=risk_score,
                impact_description=impact_description
            )
            
            session.add(attack_chain)
            session.flush()
            
            return attack_chain.id
    
    def get_attack_chains(self, session_id: str) -> List[AttackChain]:
        """Get attack chains for session"""
        with self.get_session() as session:
            results = session.query(AttackChain).filter(
                AttackChain.session_id == session_id
            ).order_by(AttackChain.risk_score.desc()).all()
            for r in results:
                session.expunge(r)
            return results
    
    # Analytics and reporting
    def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a pentest session"""
        with self.get_session() as session:
            vulnerabilities = session.query(Vulnerability).filter(Vulnerability.session_id == session_id).all()
            phases = session.query(PhaseResult).filter(PhaseResult.session_id == session_id).all()
            attack_chains = session.query(AttackChain).filter(AttackChain.session_id == session_id).all()
            
            severity_counts = {}
            for vuln in vulnerabilities:
                severity_counts[vuln.severity] = severity_counts.get(vuln.severity, 0) + 1
            
            phase_status = {}
            total_execution_time = 0
            for phase in phases:
                phase_status[phase.phase_name] = phase.status
                if phase.execution_time:
                    total_execution_time += phase.execution_time
            
            return {
                'total_vulnerabilities': len(vulnerabilities),
                'severity_distribution': severity_counts,
                'phase_status': phase_status,
                'total_execution_time': total_execution_time,
                'attack_chains_count': len(attack_chains),
                'high_risk_chains': len([chain for chain in attack_chains if chain.risk_score >= 8.0])
            }
    
    def get_historical_trends(self, days: int = 30) -> Dict[str, Any]:
        """Get historical trends for dashboard"""
        with self.get_session() as session:
            from sqlalchemy import func, and_
            from datetime import datetime, timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Session trends
            session_count = session.query(PentestSession).filter(
                PentestSession.created_at >= cutoff_date
            ).count()
            
            # Vulnerability trends
            vuln_trends = session.query(
                Vulnerability.severity,
                func.count(Vulnerability.id).label('count')
            ).filter(
                Vulnerability.discovered_at >= cutoff_date
            ).group_by(Vulnerability.severity).all()
            
            return {
                'session_count': session_count,
                'vulnerability_trends': {trend.severity: trend.count for trend in vuln_trends}
            }

# Global database manager instance
db_manager = None

def get_db_manager() -> DatabaseManager:
    """Get global database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
        db_manager.create_tables()
    return db_manager

def init_database(database_url: str = None) -> DatabaseManager:
    """Initialize database manager"""
    global db_manager
    db_manager = DatabaseManager(database_url)
    db_manager.create_tables()
    return db_manager
