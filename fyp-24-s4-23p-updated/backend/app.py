from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from db_connection import get_db, initialize_database
from auth import register_user, login_user, logout_user, require_login
from dialogflow_handler import DialogflowHandler
from notification_scheduler import schedule_notification
from appointment_scheduler import AppointmentScheduler
from payment_handler import PaymentHandler
from prescription_handler import PrescriptionHandler
from health_records_handler import HealthRecordsHandler
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize handlers
dialogflow = DialogflowHandler('chatbotproject-444010')
payment_handler = PaymentHandler()
prescription_handler = PrescriptionHandler()
health_records_handler = HealthRecordsHandler()
appointment_scheduler = AppointmentScheduler()

# Initialize database when the app starts
initialize_database()

@app.route('/')
def index():
    if 'user_id' in session:
        return render_template('index.html', user_id=session['user_id'])
    return render_template('index.html', user_id=None)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        first_name = request.form.get('first_name', username)
        last_name = request.form.get('last_name', '')
        
        success, message = register_user(
            username, 
            password, 
            email,
            first_name,
            last_name
        )
        
        if success:
            return redirect(url_for('login'))
        return render_template('register.html', error=message)
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        success, result = login_user(username, password)
        
        if success:
            session['user_id'] = result['id']
            session['username'] = result['username']
            return redirect(url_for('chat'))
        else:
            return render_template('login.html', error=result)
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'GET':
        return render_template('chat.html')
    
    # Handle POST request for chat messages
    try:
        message = request.json.get('message', '')
        user_id = session['user_id']
        
        print(f"Processing message: {message}")
        
        # Handle profile updates
        update_commands = {
            'phone': r'[Uu]pdate my (?:phone|telephone|mobile)(?: number)? to (\d+)',
            'address': r'[Uu]pdate my address to (.+)',
            'blood_type': r'[Mm]y blood type is (A\+|A-|B\+|B-|O\+|O-|AB\+|AB-)',
            'allergies': r'[Uu]pdate my allergies to (.+)',
            'emergency_contact': r'[Uu]pdate my emergency contact to (.+)'
        }
        
        for field, pattern in update_commands.items():
            import re
            match = re.search(pattern, message)
            if match:
                value = match.group(1).strip()
                try:
                    conn = get_db()
                    cursor = conn.cursor()
                    
                    if field in ['phone', 'address', 'emergency_contact']:
                        # Update users table
                        cursor.execute(f"UPDATE users SET {field} = ? WHERE id = ?", (value, user_id))
                    else:
                        # Check if profile exists
                        cursor.execute("SELECT id FROM patient_profiles WHERE user_id = ?", (user_id,))
                        profile = cursor.fetchone()
                        if not profile:
                            cursor.execute("INSERT INTO patient_profiles (user_id) VALUES (?)", (user_id,))
                        
                        # Update patient_profiles table
                        cursor.execute(f"""
                            UPDATE patient_profiles 
                            SET {field} = ?
                            WHERE user_id = ?
                        """, (value, user_id))
                    
                    conn.commit()
                    return jsonify({'response': f'✅ Your {field.replace("_", " ")} has been updated to: {value}'})
                
                except Exception as e:
                    print(f"Error updating profile: {str(e)}")
                    return jsonify({'response': f"Sorry, I couldn't update your {field.replace('_', ' ')} at this moment."})
                finally:
                    if 'conn' in locals():
                        conn.close()
        
        # Handle profile information request
        if message.lower().strip() == 'show my profile information':
            try:
                conn = get_db()
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT u.*, p.*
                    FROM users u
                    LEFT JOIN patient_profiles p ON u.id = p.user_id
                    WHERE u.id = ?
                """, (user_id,))
                
                profile = cursor.fetchone()
                if profile:
                    response = f"""👤 Your Profile Information:
📋 Name: {profile['username']}
📧 Email: {profile['email']}
📞 Phone: {profile['phone'] or 'Not provided'}
📍 Address: {profile['address'] or 'Not provided'}
🏥 Blood Type: {profile.get('blood_type') or 'Not provided'}
⚕️ Allergies: {profile.get('allergies') or 'Not provided'}
🆘 Emergency Contact: {profile['emergency_contact'] or 'Not provided'}"""
                    return jsonify({'response': response})
                else:
                    return jsonify({'response': "Sorry, I couldn't find your profile information."})
            except Exception as e:
                print(f"Error getting profile: {str(e)}")
                return jsonify({'response': "Sorry, I couldn't retrieve your profile information at this moment."})
            finally:
                if 'conn' in locals():
                    conn.close()
        
        # If not a profile update or info request, proceed with Dialogflow
        try:
            response = dialogflow.handle_intent(user_id, message)
            return jsonify({'response': response})
        except Exception as e:
            print(f"Error in Dialogflow request: {str(e)}")
            return jsonify({'response': "I'm having trouble understanding. Could you please try again?"})
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({'response': "Sorry, there was an error processing your request."})

@app.route('/change-password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        current_password = data.get('currentPassword')
        new_password = data.get('newPassword')
        
        if not current_password or not new_password:
            return jsonify({"error": "Missing required fields"}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Verify current password
        cursor.execute("SELECT password FROM users WHERE id = ?", (session['user_id'],))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        if user['password'] != current_password:
            return jsonify({"error": "Current password is incorrect"}), 400
        
        # Update password
        cursor.execute("""
            UPDATE users 
            SET password = ?
            WHERE id = ?
        """, (new_password, session['user_id']))
        
        conn.commit()
        return jsonify({"message": "Password changed successfully"})
        
    except Exception as e:
        print(f"Error changing password: {str(e)}")
        return jsonify({"error": f"Failed to change password: {str(e)}"}), 500
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    app.run(debug=True)
