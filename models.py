"""
User model and database configuration for authentication
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)  # Null for OAuth users
    name = db.Column(db.String(255), nullable=True)
    avatar_url = db.Column(db.String(500), nullable=True)
    
    # OAuth provider info
    auth_provider = db.Column(db.String(50), default='email')  # email, google, github, twitter
    oauth_id = db.Column(db.String(255), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Email verification
    email_verified = db.Column(db.Boolean, default=False)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    @staticmethod
    def get_or_create_oauth_user(email, name, avatar_url, provider, oauth_id):
        """Get existing user or create new one for OAuth login"""
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Update OAuth info if logging in with different provider
            if user.auth_provider == 'email' and provider != 'email':
                user.auth_provider = provider
                user.oauth_id = oauth_id
            user.update_last_login()
            return user
        
        # Create new user
        user = User(
            email=email,
            name=name,
            avatar_url=avatar_url,
            auth_provider=provider,
            oauth_id=oauth_id,
            email_verified=True  # OAuth emails are pre-verified
        )
        db.session.add(user)
        db.session.commit()
        return user
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'avatar_url': self.avatar_url,
            'auth_provider': self.auth_provider,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<User {self.email}>'
