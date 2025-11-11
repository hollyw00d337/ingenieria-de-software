from functools import wraps
from flask import session, jsonify, redirect, url_for, request

def require_role(allowed_roles):
    """Decorador para requerir roles específicos"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.is_json:
                    return jsonify({'error': 'No autorizado'}), 401
                return redirect(url_for('login'))
            
            user_role = session.get('role', 'user')
            if user_role not in allowed_roles:
                if request.is_json:
                    return jsonify({'error': 'Permisos insuficientes'}), 403
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def is_authenticated():
    """Verifica si el usuario está autenticado"""
    return 'user_id' in session

def get_current_user_role():
    """Obtiene el rol del usuario actual"""
    return session.get('role', 'user')
