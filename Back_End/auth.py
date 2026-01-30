from flask import Blueprint, request, jsonify
import bcrypt
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps

auth_bp = Blueprint('auth', __name__)


# Get database connection from main app
def get_db():
    from app import get_db as app_get_db
    return app_get_db()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def hash_password(password):
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def check_password(password, hashed):
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def generate_token(user_id, username):
    """Generate JWT token."""
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': datetime.utcnow() + timedelta(days=7)  # Token expires in 7 days
    }
    return jwt.encode(payload, os.getenv('JWT_SECRET'), algorithm='HS256')


def token_required(f):
    """Decorator to protect routes that require authentication."""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]

            data = jwt.decode(token, os.getenv('JWT_SECRET'), algorithms=['HS256'])
            request.current_user = data
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(*args, **kwargs)

    return decorated


# =============================================================================
# REGISTRATION
# =============================================================================

@auth_bp.route('/api/register', methods=['POST'])
def register():
    """
    Register a new user.

    Request body:
    {
        "name": "John Doe",
        "username": "johndoe",
        "email": "john@example.com",
        "password": "SecurePass123"
    }
    """
    data = request.json

    # Validate required fields
    required_fields = ['name', 'username', 'email', 'password']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    name = data['name'].strip()
    username = data['username'].strip().lower()
    email = data['email'].strip().lower()
    password = data['password']

    # Validate username format
    if len(username) < 3 or len(username) > 20:
        return jsonify({'error': 'Username must be 3-20 characters'}), 400

    if not username.replace('_', '').isalnum():
        return jsonify({'error': 'Username can only contain letters, numbers, and underscores'}), 400

    # Validate email format
    if '@' not in email or '.' not in email:
        return jsonify({'error': 'Invalid email format'}), 400

    # Validate password strength
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check if username already exists
        cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return jsonify({'error': 'Username already taken'}), 409

        # Check if email already exists
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({'error': 'Email already registered'}), 409

        # Hash password
        password_hash = hash_password(password)

        # Insert new user
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, created_at)
            VALUES (%s, %s, %s, NOW())
        """, (username,email, password_hash))

        conn.commit()
        user_id = cursor.lastrowid

        # Generate token for immediate login
        token = generate_token(user_id, username)

        return jsonify({
            'message': 'Registration successful',
            'user': {
                'user_id': user_id,
                'username': username,
                'name': name,
                'email': email
            },
            'token': token
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()


# =============================================================================
# LOGIN
# =============================================================================

@auth_bp.route('/api/login', methods=['POST'])
def login():
    """
    Login user.

    Request body:
    {
        "username": "johndoe",  (or email)
        "password": "SecurePass123"
    }
    """
    data = request.json
    print("Hello Inside login server")

    username_or_email = data.get('username', '').strip().lower()
    password = data.get('password', '')
    print("Username:",username_or_email)
    print("Password:",password)

    if not username_or_email or not password:
        return jsonify({'error': 'Username/email and password are required'}), 400

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        # Find user by username or email
        cursor.execute("""
            SELECT user_id, username, email, password_hash, user_mean, rating_count
            FROM users 
            WHERE username = %s
        """, (username_or_email,))

        user = cursor.fetchone()

        if not user:
            print("Not here")
            return jsonify({'error': 'Invalid  Credentials'}), 401

        # Verify password
        if not check_password(password, user['password_hash']):

            return jsonify({'error': 'Invalid Credentials','error_password':'Invalid Password'}), 401

        # Generate token
        token = generate_token(user['user_id'], user['username'])
        print("Token:",token)
        return jsonify({
            'message': 'Login successful',
            'user': {
                'user_id': user['user_id'],
                'username': user['username'],
                'email': user['email'],
                'name': user.get('name', user['username']),  # fallback to username if no name
                'user_mean': user.get('user_mean'),
                'rating_count': user.get('rating_count', 0)
            },
            'token': token
        })

    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()


# =============================================================================
# GET CURRENT USER (Protected Route Example)
# =============================================================================

@auth_bp.route('/api/me', methods=['GET'])
@token_required
def get_current_user():
    """Get current logged-in user details."""
    user_id = request.current_user['user_id']

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT user_id, username, name, email, user_mean, rating_count, created_at
            FROM users 
            WHERE user_id = %s
        """, (user_id,))

        user = cursor.fetchone()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({'user': user})

    finally:
        cursor.close()
        conn.close()


# =============================================================================
# UPDATE USER PROFILE (Protected)
# =============================================================================

@auth_bp.route('/api/me', methods=['PUT'])
@token_required
def update_profile():
    """Update current user's profile."""
    user_id = request.current_user['user_id']
    data = request.json

    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()

    if not name and not email:
        return jsonify({'error': 'Nothing to update'}), 400

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check if email is taken by another user
        if email:
            cursor.execute(
                "SELECT user_id FROM users WHERE email = %s AND user_id != %s",
                (email, user_id)
            )
            if cursor.fetchone():
                return jsonify({'error': 'Email already in use'}), 409

        # Build update query
        updates = []
        params = []

        if name:
            updates.append("name = %s")
            params.append(name)
        if email:
            updates.append("email = %s")
            params.append(email)

        params.append(user_id)

        cursor.execute(f"""
            UPDATE users SET {', '.join(updates)}
            WHERE user_id = %s
        """, params)

        conn.commit()

        return jsonify({'message': 'Profile updated successfully'})

    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'Update failed: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()