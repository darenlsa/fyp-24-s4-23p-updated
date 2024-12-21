import sqlite3
from db_connection import get_db
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for

def register_user(username, password, email, phone=None, address=None, emergency_contact=None):
    """Register a new user"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return False, "Username already exists"
        
        # Insert new user
        cursor.execute("""
            INSERT INTO users (username, password, email, phone, address, emergency_contact)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, password, email, phone, address, emergency_contact))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        # Create sample data for new user
        create_sample_data(user_id)
        
        return True, {"id": user_id, "username": username}
    except Exception as e:
        print(f"Error in user registration: {str(e)}")
        return False, "Registration failed"
    finally:
        if 'conn' in locals():
            conn.close()

def login_user(username, password):
    """Login a user"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, status 
            FROM users 
            WHERE username = ? AND password = ?
        """, (username, password))
        
        user = cursor.fetchone()
        
        if not user:
            return False, "Invalid username or password"
            
        if user['status'] == 'deactivated':
            return False, "Account is deactivated"
            
        return True, {"id": user['id'], "username": user['username']}
    except Exception as e:
        print(f"Error in user login: {str(e)}")
        return False, "Login failed"
    finally:
        if 'conn' in locals():
            conn.close()

def logout_user():
    """Logout a user"""
    try:
        session.clear()
        return True, "Logged out successfully"
    except Exception as e:
        print(f"Error in user logout: {str(e)}")
        return False, "Logout failed"

def create_sample_data(user_id):
    """Create sample data for a new user."""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Get user's username
        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            return False
            
        # Create patient profile with all fields set to 'Not provided'
        cursor.execute("""
            INSERT INTO patient_profiles (user_id, first_name, last_name, blood_type, allergies)
            VALUES (?, ?, '', 'Not provided', 'Not provided')
        """, (user_id, user['username']))

        conn.commit()
        print(f"Sample data created for user_id: {user_id}")
        return True
    except Exception as e:
        print(f"Error creating sample data: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

def reset_password(token, new_password):
    """Reset password using token"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Find valid token
        cursor.execute("""
            SELECT user_id FROM password_resets 
            WHERE token = ? AND expiry > CURRENT_TIMESTAMP 
            AND used = 0
        """, (token,))
        reset = cursor.fetchone()
        
        if not reset:
            return False, "Invalid or expired reset token"
        
        # Update password
        cursor.execute("""
            UPDATE users 
            SET password = ? 
            WHERE id = ?
        """, (new_password, reset['user_id']))
        
        # Mark token as used
        cursor.execute("""
            UPDATE password_resets 
            SET used = 1 
            WHERE token = ?
        """, (token,))
        
        conn.commit()
        return True, "Password reset successful"
    except Exception as e:
        print(f"Error in password reset: {str(e)}")
        return False, "Failed to reset password"
    finally:
        if 'conn' in locals():
            conn.close()

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function 