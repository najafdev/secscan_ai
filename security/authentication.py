#!/usr/bin/env python3
# SecScan AI core module
"""
Enhanced Security and Authentication System for SecScan AI
Enterprise-grade authentication, RBAC, and audit logging
"""

import os
import jwt
import bcrypt
import ldap3
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import secrets
import hashlib
from functools import wraps
from flask import request, jsonify

from database import get_db_manager, User, AuditLog

class Role(Enum):
    ADMIN = "admin"
    SENIOR_ANALYST = "senior_analyst" 
    ANALYST = "analyst"
    VIEWER = "viewer"

class Permission(Enum):
    # Session permissions
    CREATE_SESSION = "create_session"
    VIEW_SESSION = "view_session"
    DELETE_SESSION = "delete_session"
    MODIFY_SESSION = "modify_session"
    
    # Exploitation permissions
    RUN_EXPLOITATION = "run_exploitation"
    RUN_ACTIVE_SCANS = "run_active_scans"
    
    # Administrative permissions
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    SYSTEM_CONFIG = "system_config"
    
    # Reporting permissions
    VIEW_REPORTS = "view_reports"
    EXPORT_REPORTS = "export_reports"
    DELETE_REPORTS = "delete_reports"

@dataclass
class AuthResult:
    success: bool
    user_id: Optional[str]
    username: Optional[str]
    role: Optional[str]
    permissions: List[str]
    token: Optional[str]
    error_message: Optional[str]

class RoleBasedAccessControl:
    """Role-Based Access Control system"""
    
    def __init__(self):
        self.role_permissions = {
            Role.ADMIN: [p.value for p in Permission],
            Role.SENIOR_ANALYST: [
                Permission.CREATE_SESSION.value,
                Permission.VIEW_SESSION.value,
                Permission.MODIFY_SESSION.value,
                Permission.RUN_EXPLOITATION.value,
                Permission.RUN_ACTIVE_SCANS.value,
                Permission.VIEW_REPORTS.value,
                Permission.EXPORT_REPORTS.value,
                Permission.VIEW_AUDIT_LOGS.value,
            ],
            Role.ANALYST: [
                Permission.CREATE_SESSION.value,
                Permission.VIEW_SESSION.value,
                Permission.RUN_ACTIVE_SCANS.value,
                Permission.VIEW_REPORTS.value,
                Permission.EXPORT_REPORTS.value,
            ],
            Role.VIEWER: [
                Permission.VIEW_SESSION.value,
                Permission.VIEW_REPORTS.value,
            ]
        }
    
    def get_user_permissions(self, role: str) -> List[str]:
        """Get permissions for a user role"""
        try:
            role_enum = Role(role)
            return self.role_permissions.get(role_enum, [])
        except ValueError:
            return []
    
    def has_permission(self, user_role: str, permission: str) -> bool:
        """Check if user role has specific permission"""
        user_permissions = self.get_user_permissions(user_role)
        return permission in user_permissions
    
    def require_permission(self, permission: str):
        """Decorator to require specific permission"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                # Get user from request context (set by authentication middleware)
                user_role = getattr(request, 'user_role', None)
                
                if not user_role or not self.has_permission(user_role, permission):
                    return jsonify({'error': 'Insufficient permissions'}), 403
                
                return f(*args, **kwargs)
            return decorated_function
        return decorator

class ComplianceAuditLogger:
    """Comprehensive audit logging for compliance"""
    
    def __init__(self):
        self.db = get_db_manager()
        self.logger = logging.getLogger('audit')
        
        # Setup file logging for audit trail with fallback
        audit_log_path = os.getenv('AUDIT_LOG_FILE', '/var/log/secscan_ai/audit.log')
        audit_file = Path(audit_log_path)
        try:
            audit_file.parent.mkdir(parents=True, exist_ok=True)
            audit_handler = logging.FileHandler(str(audit_file))
        except (OSError, PermissionError):
            try:
                fallback_dir = Path.cwd() / 'logs'
                fallback_dir.mkdir(parents=True, exist_ok=True)
                audit_handler = logging.FileHandler(str(fallback_dir / 'audit.log'))
            except (OSError, PermissionError):
                audit_handler = logging.StreamHandler()
        audit_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        audit_handler.setFormatter(audit_formatter)
        self.logger.addHandler(audit_handler)
        self.logger.setLevel(logging.INFO)
    
    def log_authentication(self, user_id: str, status: str, ip_address: str = None, 
                          user_agent: str = None, details: Dict[str, Any] = None):
        """Log authentication events"""
        self.db.log_action(
            user_id=user_id,
            action=f'authentication_{status}',
            resource_type='authentication',
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.logger.info(f"Authentication {status} for user {user_id} from {ip_address}")
    
    def log_pentest_action(self, user_id: str, action: str, session_id: str = None, 
                          target: str = None, details: Dict[str, Any] = None):
        """Log penetration testing actions"""
        self.db.log_action(
            user_id=user_id,
            action=action,
            resource_type='pentest_session',
            resource_id=session_id,
            details={
                'target': target,
                'session_id': session_id,
                **(details or {})
            }
        )
        
        self.logger.info(f"Pentest action '{action}' by user {user_id} on {target}")
    
    def log_exploitation(self, user_id: str, target: str, exploit_type: str, 
                        success: bool, details: Dict[str, Any] = None):
        """Log exploitation attempts (critical for compliance)"""
        self.db.log_action(
            user_id=user_id,
            action='exploitation_attempt',
            resource_type='exploitation',
            details={
                'target': target,
                'exploit_type': exploit_type,
                'success': success,
                'timestamp': datetime.utcnow().isoformat(),
                **(details or {})
            }
        )
        
        status = "SUCCESS" if success else "FAILED"
        self.logger.critical(f"EXPLOITATION {status}: {exploit_type} on {target} by user {user_id}")
    
    def log_data_access(self, user_id: str, resource_type: str, resource_id: str, 
                       action: str, details: Dict[str, Any] = None):
        """Log data access for compliance tracking"""
        self.db.log_action(
            user_id=user_id,
            action=f'data_access_{action}',
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {}
        )
        
        self.logger.info(f"Data access: {action} on {resource_type}:{resource_id} by user {user_id}")
    
    def generate_compliance_report(self, start_date: datetime, end_date: datetime, 
                                 user_id: str = None) -> Dict[str, Any]:
        """Generate compliance audit report"""
        # Get audit logs for period
        audit_logs = self.db.get_audit_logs()  # Add date filtering in production
        
        report = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'statistics': {
                'total_actions': len(audit_logs),
                'unique_users': len(set(log.user_id for log in audit_logs)),
                'authentication_attempts': len([log for log in audit_logs if 'authentication' in log.action]),
                'exploitation_attempts': len([log for log in audit_logs if 'exploitation' in log.action]),
                'failed_authentications': len([log for log in audit_logs if 'authentication_failed' in log.action])
            },
            'top_actions': self._get_top_actions(audit_logs),
            'security_events': self._identify_security_events(audit_logs),
            'recommendations': self._generate_security_recommendations(audit_logs)
        }
        
        return report
    
    def _get_top_actions(self, audit_logs: List[AuditLog]) -> List[Dict[str, Any]]:
        """Get top actions from audit logs"""
        action_counts = {}
        for log in audit_logs:
            action_counts[log.action] = action_counts.get(log.action, 0) + 1
        
        return [
            {'action': action, 'count': count}
            for action, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]
    
    def _identify_security_events(self, audit_logs: List[AuditLog]) -> List[Dict[str, Any]]:
        """Identify potential security events"""
        security_events = []
        
        # Check for multiple failed authentications
        failed_auths = {}
        for log in audit_logs:
            if 'authentication_failed' in log.action:
                user_ip = f"{log.user_id}:{log.ip_address}"
                failed_auths[user_ip] = failed_auths.get(user_ip, 0) + 1
        
        for user_ip, count in failed_auths.items():
            if count >= 5:  # Threshold for suspicious activity
                security_events.append({
                    'type': 'multiple_failed_auth',
                    'user_ip': user_ip,
                    'count': count,
                    'severity': 'high' if count >= 10 else 'medium'
                })
        
        return security_events
    
    def _generate_security_recommendations(self, audit_logs: List[AuditLog]) -> List[str]:
        """Generate security recommendations based on audit logs"""
        recommendations = []
        
        # Check authentication patterns
        failed_auth_count = len([log for log in audit_logs if 'authentication_failed' in log.action])
        total_auth_count = len([log for log in audit_logs if 'authentication' in log.action])
        
        if total_auth_count > 0 and (failed_auth_count / total_auth_count) > 0.2:
            recommendations.append("High authentication failure rate detected. Consider implementing account lockout policies.")
        
        # Check exploitation activity
        exploit_count = len([log for log in audit_logs if 'exploitation' in log.action])
        if exploit_count > 100:  # Threshold
            recommendations.append("High exploitation activity detected. Ensure proper authorization and monitoring.")
        
        return recommendations

class LDAPAuthenticator:
    """LDAP/Active Directory authentication"""
    
    def __init__(self, server_url: str, base_dn: str, bind_dn: str = None, bind_password: str = None):
        self.server_url = server_url
        self.base_dn = base_dn
        self.bind_dn = bind_dn
        self.bind_password = bind_password
        self.logger = logging.getLogger(__name__)
    
    def authenticate(self, username: str, password: str) -> AuthResult:
        """Authenticate user against LDAP"""
        try:
            # Create LDAP connection
            server = ldap3.Server(self.server_url, get_info=ldap3.ALL)
            
            # Bind with service account if provided
            if self.bind_dn and self.bind_password:
                conn = ldap3.Connection(server, self.bind_dn, self.bind_password, auto_bind=True)
            else:
                conn = ldap3.Connection(server, auto_bind=True)
            
            # Search for user (sanitize username to prevent LDAP injection)
            from ldap3.utils.conv import escape_filter_chars
            safe_username = escape_filter_chars(username)
            search_filter = f"(sAMAccountName={safe_username})"
            conn.search(self.base_dn, search_filter, attributes=['displayName', 'mail', 'memberOf'])
            
            if not conn.entries:
                return AuthResult(False, None, None, None, [], None, "User not found")
            
            user_entry = conn.entries[0]
            user_dn = user_entry.entry_dn
            
            # Attempt authentication with user credentials
            user_conn = ldap3.Connection(server, user_dn, password)
            
            if not user_conn.bind():
                return AuthResult(False, None, None, None, [], None, "Invalid credentials")
            
            # Extract user information
            display_name = str(user_entry.displayName) if user_entry.displayName else username
            email = str(user_entry.mail) if user_entry.mail else f"{username}@domain.com"
            
            # Determine role based on group membership
            role = self._determine_role_from_groups(user_entry.memberOf)
            
            # Create or update user in database
            db = get_db_manager()
            existing_user = db.get_user_by_username(username)
            
            if not existing_user:
                user_id = db.create_user(username, email, "ldap_user", role)
            else:
                user_id = existing_user.id
                db.update_user_login(user_id)
            
            # Get permissions
            rbac = RoleBasedAccessControl()
            permissions = rbac.get_user_permissions(role)
            
            # Generate JWT token
            token = self._generate_jwt_token(user_id, username, role)
            
            conn.unbind()
            user_conn.unbind()
            
            return AuthResult(True, user_id, username, role, permissions, token, None)
            
        except Exception as e:
            self.logger.error(f"LDAP authentication error: {e}")
            return AuthResult(False, None, None, None, [], None, f"Authentication error: {str(e)}")
    
    def _determine_role_from_groups(self, member_of) -> str:
        """Determine user role based on AD group membership"""
        if not member_of:
            return Role.VIEWER.value
        
        # Convert to strings for checking
        groups = [str(group).lower() for group in member_of]
        
        # Check for admin groups
        if any('secscan_ai-admin' in group or 'pentest-admin' in group for group in groups):
            return Role.ADMIN.value
        elif any('secscan_ai-senior' in group or 'pentest-senior' in group for group in groups):
            return Role.SENIOR_ANALYST.value
        elif any('secscan_ai-analyst' in group or 'pentest-analyst' in group for group in groups):
            return Role.ANALYST.value
        else:
            return Role.VIEWER.value
    
    def _generate_jwt_token(self, user_id: str, username: str, role: str) -> str:
        """Generate JWT token for user"""
        payload = {
            'user_id': user_id,
            'username': username,
            'role': role,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=8)  # 8 hour expiration
        }
        
        secret_key = os.getenv('JWT_SECRET_KEY') or os.getenv('SECRET_KEY')
        if not secret_key:
            raise ValueError("JWT_SECRET_KEY or SECRET_KEY must be set in environment")
        return jwt.encode(payload, secret_key, algorithm='HS256')

class LocalAuthenticator:
    """Local database authentication"""
    
    def __init__(self):
        self.db = get_db_manager()
        self.logger = logging.getLogger(__name__)
    
    def authenticate(self, username: str, password: str) -> AuthResult:
        """Authenticate user against local database"""
        try:
            user = self.db.get_user_by_username(username)
            
            if not user:
                return AuthResult(False, None, None, None, [], None, "User not found")
            
            if not user.is_active:
                return AuthResult(False, None, None, None, [], None, "Account disabled")
            
            # Verify password
            if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
                return AuthResult(False, None, None, None, [], None, "Invalid credentials")
            
            # Update last login
            self.db.update_user_login(user.id)
            
            # Get permissions
            rbac = RoleBasedAccessControl()
            permissions = rbac.get_user_permissions(user.role)
            
            # Generate JWT token
            token = self._generate_jwt_token(user.id, user.username, user.role)
            
            return AuthResult(True, user.id, user.username, user.role, permissions, token, None)
            
        except Exception as e:
            self.logger.error(f"Local authentication error: {e}")
            return AuthResult(False, None, None, None, [], None, f"Authentication error: {str(e)}")
    
    def create_user(self, username: str, email: str, password: str, role: str = Role.ANALYST.value) -> str:
        """Create new local user"""
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create user in database
        user_id = self.db.create_user(username, email, password_hash, role)
        
        return user_id
    
    def _generate_jwt_token(self, user_id: str, username: str, role: str) -> str:
        """Generate JWT token for user"""
        payload = {
            'user_id': user_id,
            'username': username,
            'role': role,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=8)  # 8 hour expiration
        }
        
        secret_key = os.getenv('JWT_SECRET_KEY') or os.getenv('SECRET_KEY')
        if not secret_key:
            raise ValueError("JWT_SECRET_KEY or SECRET_KEY must be set in environment")
        return jwt.encode(payload, secret_key, algorithm='HS256')

class EnterpriseAuth:
    """Enterprise authentication system"""
    
    def __init__(self):
        self.rbac = RoleBasedAccessControl()
        self.audit_logger = ComplianceAuditLogger()
        
        # Initialize authenticators based on configuration
        self.authenticators = {}
        
        # Local authenticator (always available)
        self.authenticators['local'] = LocalAuthenticator()
        
        # LDAP authenticator (if configured)
        ldap_server = os.getenv('LDAP_SERVER')
        ldap_base_dn = os.getenv('LDAP_BASE_DN')
        if ldap_server and ldap_base_dn:
            self.authenticators['ldap'] = LDAPAuthenticator(
                ldap_server,
                ldap_base_dn,
                os.getenv('LDAP_BIND_DN'),
                os.getenv('LDAP_BIND_PASSWORD')
            )
        
        self.logger = logging.getLogger(__name__)
    
    def authenticate_user(self, username: str, password: str, method: str = 'local', 
                         ip_address: str = None, user_agent: str = None) -> AuthResult:
        """Authenticate user with specified method"""
        if method not in self.authenticators:
            return AuthResult(False, None, None, None, [], None, f"Authentication method '{method}' not available")
        
        # Attempt authentication
        result = self.authenticators[method].authenticate(username, password)
        
        # Log authentication attempt
        if result.success:
            self.audit_logger.log_authentication(
                result.user_id, 'success', ip_address, user_agent,
                {'method': method, 'username': username}
            )
        else:
            # For failed attempts, log with username since we don't have user_id
            self.audit_logger.log_authentication(
                username, 'failed', ip_address, user_agent,
                {'method': method, 'error': result.error_message}
            )
        
        return result
    
    def verify_token(self, token: str) -> AuthResult:
        """Verify JWT token"""
        try:
            secret_key = os.getenv('JWT_SECRET_KEY') or os.getenv('SECRET_KEY')
            if not secret_key:
                return AuthResult(False, None, None, None, [], None, "Server JWT secret not configured")
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            # Get user permissions
            permissions = self.rbac.get_user_permissions(payload['role'])
            
            return AuthResult(
                True, payload['user_id'], payload['username'], 
                payload['role'], permissions, token, None
            )
            
        except jwt.ExpiredSignatureError:
            return AuthResult(False, None, None, None, [], None, "Token expired")
        except jwt.InvalidTokenError as e:
            return AuthResult(False, None, None, None, [], None, f"Invalid token: {str(e)}")
    
    def require_auth(self, f):
        """Decorator to require authentication"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get token from Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Authentication required'}), 401
            
            token = auth_header.split(' ')[1]
            auth_result = self.verify_token(token)
            
            if not auth_result.success:
                return jsonify({'error': auth_result.error_message}), 401
            
            # Add user info to request context
            request.user_id = auth_result.user_id
            request.username = auth_result.username
            request.user_role = auth_result.role
            request.user_permissions = auth_result.permissions
            
            return f(*args, **kwargs)
        return decorated_function
    
    def require_permission(self, permission: str):
        """Decorator to require specific permission"""
        return self.rbac.require_permission(permission)
