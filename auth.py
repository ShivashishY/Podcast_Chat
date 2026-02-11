"""
Authentication module - Email only
"""
import os
import secrets
import logging
from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def get_or_create_secret_key():
    """Get secret key from file or generate a new one"""
    secret_file = os.path.join(os.path.dirname(__file__), '.secret_key')
    if os.path.exists(secret_file):
        with open(secret_file, 'r') as f:
            return f.read().strip()
    else:
        key = secrets.token_hex(32)
        with open(secret_file, 'w') as f:
            f.write(key)
        return key


def init_auth(app):
    """Initialize authentication for the Flask app"""
    
    # Database config
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = get_or_create_secret_key()
    
    # Initialize database
    db.init_app(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Register auth blueprint
    app.register_blueprint(auth_bp)
    
    logger.info("Authentication initialized (email-only)")


# ============ Page Routes ============

@auth_bp.route('/login')
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('login.html')


@auth_bp.route('/signup')
def signup():
    """Signup page"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    return render_template('signup.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Log out the current user"""
    logout_user()
    return redirect(url_for('auth.login'))


# ============ Email Authentication ============

@auth_bp.route('/email/signup', methods=['POST'])
def email_signup():
    """Handle email signup"""
    data = request.get_json()
    
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400
    
    # Check if user exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'error': 'An account with this email already exists'}), 400
    
    # Create new user
    user = User(email=email, name=name or email.split('@')[0])
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    login_user(user)
    logger.info(f"New user registered: {email}")
    
    return jsonify({'success': True, 'user': user.to_dict()})


@auth_bp.route('/email/login', methods=['POST'])
def email_login():
    """Handle email login"""
    data = request.get_json()
    
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    login_user(user)
    logger.info(f"User logged in: {email}")
    
    return jsonify({'success': True, 'user': user.to_dict()})


# ============ API Routes ============

@auth_bp.route('/me')
def get_current_user():
    """Get current user info"""
    if current_user.is_authenticated:
        return jsonify({'authenticated': True, 'user': current_user.to_dict()})
    return jsonify({'authenticated': False})


@auth_bp.route('/check')
def check_auth():
    """Check if user is authenticated"""
    return jsonify({'authenticated': current_user.is_authenticated})
