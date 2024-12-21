from google.cloud import dialogflow_v2 as dialogflow
from google.protobuf.json_format import MessageToDict
from google.oauth2 import service_account
from db_connection import get_db
import os
import json
from datetime import datetime, timedelta
from health_reminders_handler import HealthRemindersHandler
from appointment_scheduler import AppointmentScheduler

class DialogflowHandler:
    def __init__(self, project_id):
        self.project_id = project_id
        self.appointment_scheduler = AppointmentScheduler()
        
        credentials_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'dialogflow_key',
            'chatbotproject-444010-cfe5f28c003c.json'
        ))
        
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        
        try:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=[
                    "https://www.googleapis.com/auth/dialogflow",
                    "https://www.googleapis.com/auth/cloud-platform"
                ]
            )
            self.session_client = dialogflow.SessionsClient(credentials=credentials)
            print("Dialogflow client initialized successfully")
        except Exception as e:
            print(f"Error initializing Dialogflow client: {str(e)}")
            raise

        self.health_reminders = HealthRemindersHandler()

    def get_user_appointments(self, user_id):
        try:
            print(f"Fetching appointments for user_id: {user_id}")
            if not user_id:
                return "Please log in to view your appointments."
                
            conn = get_db()
            cursor = conn.cursor()
            
            query = """
                SELECT 
                    id,
                    appointment_date,
                    appointment_time,
                    doctor_name,
                    appointment_type,
                    status
                FROM appointments 
                WHERE user_id = ? 
                AND date(appointment_date) >= date('now', 'localtime')
                AND status != 'cancelled'
                ORDER BY date(appointment_date), time(appointment_time)
            """
            print(f"Executing query: {query} with user_id: {user_id}")
            cursor.execute(query, (user_id,))
            appointments = cursor.fetchall()
            print(f"Found {len(appointments) if appointments else 0} appointments")
            
            if not appointments:
                return "You don't have any upcoming appointments scheduled."
            
            response = "📅 Your upcoming appointments:\n\n"
            for apt in appointments:
                response += f"🗓 ID: {apt['id']}\n"
                response += f"🗓️ Date: {apt['appointment_date']}\n"
                response += f"⏰ Time: {apt['appointment_time']}\n"
                response += f"👨‍⚕️ Doctor: Dr. {apt['doctor_name']}\n"
                response += f"📋 Type: {apt['appointment_type']}\n"
                response += f"📊 Status: {apt['status'].title()}\n"
                response += "─────────────────\n"
            return response
        except Exception as e:
            print(f"Error fetching appointments: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return "Sorry, I couldn't retrieve your appointments at this moment."
        finally:
            if 'conn' in locals():
                conn.close()

    def get_user_prescriptions(self, user_id, status='active'):
        """Get user prescriptions with detailed information"""
        try:
            print(f"Fetching prescriptions for user_id: {user_id}")
            conn = get_db()
            cursor = conn.cursor()
            
            # First verify the table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='prescriptions'
            """)
            if not cursor.fetchone():
                print("Prescriptions table does not exist, initializing database...")
                from db_connection import initialize_database
                initialize_database()
                conn = get_db()
                cursor = conn.cursor()
            
            if status == 'active':
                query = """
                    SELECT * FROM prescriptions 
                    WHERE user_id = ? 
                    AND status = 'active'
                    AND (end_date IS NULL OR date(end_date) >= date('now'))
                    ORDER BY created_at DESC
                """
            else:
                query = """
                    SELECT * FROM prescriptions 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC
                """
            
            print(f"Executing query: {query} with user_id: {user_id}")
            cursor.execute(query, (user_id,))
            prescriptions = cursor.fetchall()
            print(f"Found {len(prescriptions) if prescriptions else 0} prescriptions")

            if not prescriptions:
                return "You don't have any active prescriptions at the moment."

            response = "💊 Your Prescriptions:\n\n"
            for rx in prescriptions:
                response += f"🏥 Medication: {rx['medication_name']}\n"
                response += f"💊 Dosage: {rx['dosage']}\n"
                response += f"⏰ Frequency: {rx['frequency']}\n"
                
                if rx['start_date']:
                    response += f"📅 Start Date: {rx['start_date']}\n"
                if rx['end_date']:
                    response += f"📅 End Date: {rx['end_date']}\n"
                
                response += f"🔄 Refills Remaining: {rx['refills_remaining']}\n"
                response += f"📊 Status: {rx['status'].title()}\n"
                response += "─────────────────\n"

            if status == 'active':
                response += "\n💡 Need a refill? Just ask 'I need a refill for [medication name]'"
            return response
            
        except Exception as e:
            print(f"Error fetching prescriptions: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return "Sorry, I couldn't retrieve your prescriptions at this moment."
        finally:
            if 'conn' in locals():
                conn.close()

    def get_billing_info(self, user_id):
        try:
            print(f"Fetching billing info for user_id: {user_id}")
            conn = get_db()
            cursor = conn.cursor()
            
            query = """
                SELECT amount, due_date, status, description 
                FROM bills 
                WHERE user_id = ? AND status = 'PENDING'
                ORDER BY due_date
            """
            print(f"Executing query: {query} with user_id: {user_id}")
            cursor.execute(query, (user_id,))
            bills = cursor.fetchall()
            print(f"Found {len(bills) if bills else 0} bills")

            if not bills:
                return "You don't have any outstanding bills."

            response = "💰 Your billing information:\n\n"
            total = 0
            for bill in bills:
                response += f"📝 Service: {bill['description']}\n"
                response += f"💵 Amount: ${bill['amount']:.2f}\n"
                response += f"📅 Due date: {bill['due_date']}\n"
                response += f"📊 Status: {bill['status']}\n"
                response += "─────────────────\n"
                total += float(bill['amount'])
            response += f"\n💳 Total outstanding: ${total:.2f}"
            return response
        except Exception as e:
            print(f"Error fetching billing info: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return "Sorry, I couldn't retrieve your billing information at this moment."
        finally:
            if 'conn' in locals():
                conn.close()

    def get_health_records(self, user_id):
        try:
            print(f"Fetching health records for user_id: {user_id}")
            conn = get_db()
            cursor = conn.cursor()
            
            query = """
                SELECT p.*, u.email, u.phone, u.address, u.emergency_contact
                FROM patient_profiles p
                JOIN users u ON p.user_id = u.id
                WHERE p.user_id = ?
            """
            print(f"Executing query: {query} with user_id: {user_id}")
            cursor.execute(query, (user_id,))
            profile = cursor.fetchone()
            print(f"Found profile: {bool(profile)}")

            if not profile:
                return "Profile information not found."

            response = "👤 Your Profile Information:\n\n"
            response += f"📋 Name: {profile['first_name']} {profile['last_name']}\n"
            response += f"📧 Email: {profile['email']}\n"
            response += f"📞 Phone: {profile['phone'] or 'Not provided'}\n"
            response += f"📍 Address: {profile['address'] or 'Not provided'}\n"
            response += f"🏥 Blood Type: {profile['blood_type'] or 'Not provided'}\n"
            response += f"⚕️ Allergies: {profile['allergies'] or 'None'}\n"
            response += f"🆘 Emergency Contact: {profile['emergency_contact'] or 'Not provided'}\n"
            return response
        except Exception as e:
            print(f"Error fetching health records: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return "Sorry, I couldn't retrieve your profile information at this moment."
        finally:
            if 'conn' in locals():
                conn.close()

    def get_clinic_info(self, info_type):
        """Get clinic information based on type"""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clinic_info LIMIT 1")
        info = cursor.fetchone()
        conn.close()

        if not info:
            return {'text': "Sorry, clinic information is not available at the moment.", 'data': None}

        if info_type == 'opening_hours':
            return {
                'text': f"🕒 Our clinic hours are:\n{info['opening_hours']}\n\n. Need to schedule an appointment?",
                'data': info
            }
        elif info_type == 'location':
            return {
                'text': f"📍 We are located at:\n{info['address']}\n\n🗺️ Map: {info['map_link']}\n\nWould you like directions?",
                'data': info
            }
        elif info_type == 'contact':
            return {
                'text': f"📞 Phone: {info['phone']}\n📧 Email: {info['email']}\n⏰ Support Hours: {info['support_hours']}\n\nHow can we help you today?",
                'data': info
            }
        elif info_type == 'all':
            return {
                'text': f"""📍 Clinic Information:
🏥 {info['name']}
📍 Address: {info['address']}
📞 Phone: {info['phone']}
📧 Email: {info['email']}
🕒 Hours: {info['opening_hours']}
⏰ Support: {info['support_hours']}
🗺️ Map: {info['map_link']}

Would you like to schedule an appointment?""",
                'data': info
            }
        return {'text': None, 'data': None}

    def get_doctors_info(self, speciality=None):
        """Get information about available doctors"""
        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Normalize speciality name
            if speciality and 'general' in speciality.lower():
                speciality = 'General Practice'
            
            if speciality:
                cursor.execute("""
                    SELECT * FROM doctors 
                    WHERE status = 'active' AND speciality = ?
                    ORDER BY name
                """, (speciality,))
            else:
                cursor.execute("""
                    SELECT * FROM doctors 
                    WHERE status = 'active'
                    ORDER BY speciality, name
                """)
            
            doctors = cursor.fetchall()
            
            if not doctors:
                if speciality:
                    return f"I'm having trouble understanding. Could you please try again?"
                return "I'm having trouble understanding. Could you please try again?"
            
            response = "I'll help you schedule an appointment. Here are our available doctors:\n\n"
            
            for doctor in doctors:
                response += f"👨‍⚕️ Dr. {doctor['name']} - {doctor['speciality']}\n"
                if doctor['schedule']:
                    try:
                        import json
                        schedule_dict = json.loads(doctor['schedule'])
                        response += "Available slots for tomorrow:\n"
                        for time in ["9:00 AM", "10:00 AM", "11:00 AM"]:
                            response += f"- {time}\n"
                    except:
                        response += "Schedule available upon request\n"
                response += "\n"
            
            response += "Please choose a doctor and time slot."
            return response
            
        except Exception as e:
            print(f"Error getting doctors info: {str(e)}")
            return "I'm having trouble understanding. Could you please try again?"
        finally:
            if conn:
                conn.close()

    def get_available_services(self, category=None):
        """Get available clinic services"""
        conn = get_db()
        cursor = conn.cursor()
        
        if category:
            cursor.execute("SELECT * FROM clinic_services WHERE category = ? AND status = 'active'", (category,))
        else:
            cursor.execute("SELECT * FROM clinic_services WHERE status = 'active' ORDER BY category")
            
        services = cursor.fetchall()
        conn.close()

        if not services:
            return "I'm having trouble understanding. Could you please try again?"

        response = "Here are our available services:\n\n"
        current_category = None
        
        category_emojis = {
            'General': '👨‍⚕️',
            'Specialist': '🏥',
            'Laboratory': '🔬',
            'Emergency': '🚑',
            'Preventive': '💉'
        }
        
        for service in services:
            if current_category != service['category']:
                current_category = service['category']
                emoji = category_emojis.get(current_category, '🏥')
                response += f"\n{emoji} {current_category}:\n"
            
            response += f"- {service['name']}\n"
            if service['description']:
                response += f"  {service['description']}\n"
        
        return response

    def get_post_care_info(self, user_id, procedure_name=None):
        instructions = self.health_reminders.get_post_care_instructions(user_id, procedure_name)
        if not instructions:
            return "No post-care instructions found."
        
        response = "📋 Post-Care Instructions:\n\n"
        for inst in instructions:
            response += f"🏥 Procedure: {inst['procedure_name']}\n"
            response += f"📝 Instructions: {inst['instructions']}\n"
            if inst['side_effects']:
                response += f"⚠️ Possible Side Effects: {inst['side_effects']}\n"
            if inst['follow_up_date']:
                response += f"📅 Follow-up Date: {inst['follow_up_date']}\n"
            response += "─────────────────\n"
        return response

    def get_health_advice(self, category=None):
        advice = self.health_reminders.get_health_advice(category)
        if not advice:
            return "No health advice found."
        
        response = "🏥 Health Advice:\n\n"
        for item in advice:
            response += f"📌 {item['title']}\n"
            response += f"📝 {item['content']}\n"
            response += "─────────────────\n"
        return response

    def get_health_events(self):
        events = self.health_reminders.get_upcoming_events()
        if not events:
            return "No upcoming health events found."
        
        response = "🎯 Upcoming Health Events:\n\n"
        for event in events:
            response += f"📌 {event['title']}\n"
            response += f"📝 {event['description']}\n"
            response += f"📅 Date: {event['event_date']}\n"
            response += f"📍 Location: {event['location']}\n"
            response += "──────────────\n"
        return response

    def handle_appointment_scheduling(self, user_id, query, parameters):
        """Handle appointment scheduling with a more interactive flow"""
        try:
            print(f"Processing appointment scheduling for user {user_id}")
            print(f"Query: {query}")
            print(f"Parameters: {parameters}")
            
            # Parse appointment details from query
            query_lower = query.lower()
            appointment_info = self._parse_appointment_query(query_lower)
            
            if appointment_info.get('is_complete'):
                print(f"Scheduling appointment with info: {appointment_info}")
                # Schedule the appointment
                appointment_id = self.appointment_scheduler.schedule_appointment(
                    user_id,  # Use actual user_id here
                    appointment_info['doctor'],
                    appointment_info['date'],
                    appointment_info['type'],  # Use parsed type
                    appointment_info['time']
                )
                
                if appointment_id:
                    return f"""✅ Appointment scheduled successfully!
📅 Date: {appointment_info['date']}
⏰ Time: {appointment_info['time']}
👨‍⚕️ Doctor: Dr. {appointment_info['doctor']}
📋 Type: {appointment_info['type']}

Your appointment has been confirmed."""
                else:
                    # Get available slots for the requested date
                    available_slots = self.appointment_scheduler.get_available_slots(appointment_info['date'])
                    if available_slots:
                        response = "Sorry, that slot is not available. Here are the available slots for tomorrow:\n\n"
                        current_doctor = None
                        for slot in available_slots:
                            if current_doctor != slot['doctor']:
                                current_doctor = slot['doctor']
                                response += f"\n👨‍⚕️ Dr. {current_doctor}:\n"
                            response += f"⏰ {slot['time']}\n"
                        return response
                    else:
                        return "Sorry, there are no available slots for tomorrow. Would you like to try another day?"
            
            # If we don't have complete info, ask for missing details
            missing = []
            if not appointment_info.get('date'):
                missing.append("preferred date")
            if not appointment_info.get('time'):
                missing.append("preferred time")
            if not appointment_info.get('doctor'):
                missing.append("preferred doctor")
            
            if missing:
                return f"Please provide the following information: {', '.join(missing)}"
            
            return "Please provide your appointment details in this format: 'I want a [type] with Dr. [name] on [date] at [time]'"
            
        except Exception as e:
            print(f"Error in appointment scheduling: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return "Sorry, there was an error processing your request. Please try again."

    def _parse_appointment_query(self, query):
        """Parse appointment details from query"""
        info = {
            'date': None,
            'time': None,
            'doctor': None,
            'type': None,
            'is_complete': False
        }
        
        try:
            # Extract doctor name
            if "dr." in query or "dr " in query:
                parts = query.split("dr.")
                if len(parts) > 1:
                    info['doctor'] = parts[1].split()[0].strip().title()
                else:
                    parts = query.split("dr ")
                    if len(parts) > 1:
                        info['doctor'] = parts[1].split()[0].strip().title()
            
            # Extract date
            if "tomorrow" in query:
                info['date'] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Extract time
            if "pm" in query or "am" in query:
                try:
                    # Find time pattern like "2 PM" or "2:30 PM"
                    words = query.split()
                    for i, word in enumerate(words):
                        if word.lower() in ['am', 'pm']:
                            time_str = words[i-1] + ' ' + word
                            time_obj = datetime.strptime(time_str, '%I %p')
                            info['time'] = time_obj.strftime('%H:%M')
                            break
                except Exception as e:
                    print(f"Error parsing time: {str(e)}")
            
            # Extract appointment type
            if "general checkup" in query or "checkup" in query:
                info['type'] = "General Checkup"
            elif "specialist" in query:
                info['type'] = "Specialist Consultation"
            elif "follow" in query and "up" in query:
                info['type'] = "Follow-up"
            else:
                info['type'] = "General Checkup"  # Default type
            
            # Check if we have all required info
            info['is_complete'] = all([info['date'], info['time'], info['doctor']])
            print(f"Parsed appointment info: {info}")
            return info
            
        except Exception as e:
            print(f"Error parsing appointment query: {str(e)}")
            return info

    def update_health_records(self, user_id, field, value):
        """Update specific field in user's health records"""
        try:
            print(f"Updating {field} to {value} for user_id: {user_id}")
            conn = get_db()
            cursor = conn.cursor()
            
            # Map common terms to database fields
            field_mapping = {
                'phone': ('users', 'phone'),
                'telephone': ('users', 'phone'),
                'mobile': ('users', 'phone'),
                'address': ('users', 'address'),
                'location': ('users', 'address'),
                'blood type': ('patient_profiles', 'blood_type'),
                'bloodtype': ('patient_profiles', 'blood_type'),
                'blood': ('patient_profiles', 'blood_type'),
                'allergies': ('patient_profiles', 'allergies'),
                'allergy': ('patient_profiles', 'allergies'),
                'emergency contact': ('users', 'emergency_contact'),
                'emergency': ('users', 'emergency_contact'),
                'contact': ('users', 'emergency_contact')
            }
            
            field_lower = field.lower().strip()
            if field_lower not in field_mapping:
                valid_fields = list(set([k.replace('_', ' ') for k in field_mapping.keys()]))
                return f"Sorry, I can't update {field}. Valid fields are: {', '.join(valid_fields)}"
            
            table, db_field = field_mapping[field_lower]
            
            # Check if profile exists for patient_profiles updates
            if table == 'patient_profiles':
                cursor.execute("SELECT id FROM patient_profiles WHERE user_id = ?", (user_id,))
                profile = cursor.fetchone()
                if not profile:
                    # Create profile if it doesn't exist
                    cursor.execute("""
                        INSERT INTO patient_profiles (user_id)
                        VALUES (?)
                    """, (user_id,))
            
            # Update the appropriate table
            if table == 'users':
                query = f"UPDATE users SET {db_field} = ? WHERE id = ?"
            else:
                query = f"UPDATE patient_profiles SET {db_field} = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?"
            
            print(f"Executing query: {query}")
            cursor.execute(query, (value, user_id))
            
            if cursor.rowcount == 0:
                return f"Sorry, I couldn't find your profile to update {field}"
            
            conn.commit()
            return f"✅ Your {field} has been updated to: {value}"
            
        except Exception as e:
            print(f"Error updating health records: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return f"Sorry, I couldn't update your {field} at this moment."
        finally:
            if 'conn' in locals():
                conn.close()

    def handle_intent(self, user_id, query, language_code='en'):
        """Handle user intents"""
        try:
            if not user_id:
                return "Please log in to continue."
                
            print(f"Processing intent for user {user_id}")
            print(f"Query: {query}")
            
            query_lower = query.lower().strip()
            
            # Handle account deactivation requests
            deactivation_phrases = [
                "deactivate my account",
                "delete my account",
                "close my account",
                "remove my account",
                "deactivate account",
                "delete account"
            ]
            
            if any(phrase in query_lower for phrase in deactivation_phrases):
                return self.handle_account_deactivation_request(user_id)
            
            # Remove "You:" prefix if present
            if query_lower.startswith("you:"):
                query_lower = query_lower[4:].strip()
            
            # Doctor-related queries
            if "doctor" in query_lower or "doctors" in query_lower:
                speciality = None
                if "general" in query_lower:
                    speciality = "General Practice"
                elif any(spec in query_lower for spec in ["cardiology", "pediatrics", "dermatology"]):
                    for spec in ["cardiology", "pediatrics", "dermatology"]:
                        if spec in query_lower:
                            speciality = spec.title()
                            break
                return self.get_doctors_info(speciality)
            
            # Clinic information queries
            if "clinic" in query_lower:
                if "hour" in query_lower or "time" in query_lower or "open" in query_lower:
                    return self.get_clinic_info('opening_hours')['text']
                elif "location" in query_lower or "address" in query_lower or "where" in query_lower:
                    return self.get_clinic_info('location')['text']
                elif "contact" in query_lower or "phone" in query_lower or "email" in query_lower:
                    return self.get_clinic_info('contact')['text']
                else:
                    return self.get_clinic_info('all')['text']
            
            # Direct commands handling - ORDERED BY SPECIFICITY
            if "show" in query_lower:
                # Appointments
                if "appointment" in query_lower or "appointments" in query_lower:
                    print("Handling show appointments command")
                    return self.get_user_appointments(user_id)
                    
                # Prescriptions
                if "prescription" in query_lower or "prescriptions" in query_lower:
                    print("Handling show prescriptions command")
                    return self.get_user_prescriptions(user_id)
                    
                # Billing/Bills
                if "bill" in query_lower or "billing" in query_lower:
                    print("Handling show billing command")
                    return self.get_billing_info(user_id)
                    
                # Profile
                if "profile" in query_lower:
                    print("Handling show profile command")
                    return self.get_health_records(user_id)
            
            # Help with profile update
            if "how" in query_lower and "update" in query_lower and "profile" in query_lower:
                return """You can update your profile information using these commands:
• Update my phone to [your phone number]
• Update my address to [your address]
• Update my blood type to [your blood type]
• Update my allergies to [your allergies]
• Update my emergency contact to [contact info]

For example: "Update my phone to +1234567890" or "My blood type is A+"
"""
            
            # Appointment scheduling
            if any(word in query_lower for word in ["schedule", "book", "appointment", "checkup", "want"]):
                print("Handling appointment scheduling")
                return self.handle_appointment_scheduling(user_id, query_lower, {})
            
            # Prescription-related queries
            if any(word in query_lower for word in ["prescription", "medicine", "medication", "refill"]):
                # Check for specific medication name
                medication_name = None
                words = query_lower.split()
                for i, word in enumerate(words):
                    if word in ["for", "of"]:
                        if i + 1 < len(words):
                            medication_name = words[i + 1]
                            break
                
                if "active" in query_lower:
                    return self.get_user_prescriptions(user_id, 'active')
                elif "all" in query_lower:
                    return self.get_user_prescriptions(user_id, 'all')
                elif medication_name:
                    return self.handle_prescription_request(user_id, medication_name)
                else:
                    return self.get_user_prescriptions(user_id)
            
            # If no direct match, use Dialogflow
            session = self.session_client.session_path(self.project_id, str(user_id))
            text_input = dialogflow.TextInput(text=query, language_code=language_code)
            query_input = dialogflow.QueryInput(text=text_input)
            
            try:
                response = self.session_client.detect_intent(
                    request={"session": session, "query_input": query_input}
                )
                
                if response.query_result.fulfillment_text:
                    return response.query_result.fulfillment_text
                
                return "I'm not sure how to help with that. Could you please rephrase?"
                
            except Exception as e:
                print(f"Error in Dialogflow request: {str(e)}")
                return "I'm having trouble understanding. Could you please try again?"
                
        except Exception as e:
            print(f"Error in handle_intent: {str(e)}")
            return "Sorry, I encountered an error. Please try again later."

    def get_service_info(self, service_type):
        """Get detailed information about a specific service"""
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM clinic_services 
                WHERE LOWER(name) LIKE ? OR LOWER(category) LIKE ?
            """, (f"%{service_type.lower()}%", f"%{service_type.lower()}%"))
            
            service = cursor.fetchone()
            if service:
                response = f" {service['name']}\n\n"
                response += f"Description: {service['description']}\n"
                if service['duration']:
                    response += f"Duration: {service['duration']} minutes\n"
                if service['price']:
                    response += f"Price: ${service['price']}\n"
                response += "\nWould you like to schedule an appointment for this service?"
                return response
            return f"I couldn't find specific information about {service_type}. Here are our available services:\n\n" + self.get_available_services()
        
        finally:
            conn.close()

    def handle_appointment_confirmation(self, session_id):
        """Handle appointment confirmation"""
        if 'pending_appointment' not in session:
            return "There's no pending appointment to confirm."
        
        appointment = session['pending_appointment']
        success = self.appointment_scheduler.confirm_appointment(appointment['id'])
        
        if success:
            session.pop('pending_appointment', None)
            return f"""✅ Great! Your appointment has been confirmed:
📅 Date: {appointment['date']}
⏰ Time: {appointment['time']}
👨‍⚕️ Doctor: Dr. {appointment['doctor']}
📋 Type: {appointment['type']}

You will receive a confirmation email shortly. Would you like me to set a reminder for you?"""
        return "Sorry, there was an error confirming your appointment. Please try booking again."

    def handle_appointment_cancellation(self, session_id):
        """Handle appointment cancellation"""
        if 'pending_appointment' in session:
            appointment = session.pop('pending_appointment')
            self.appointment_scheduler.cancel_appointment(appointment['id'], session_id)
            return """I've cancelled the pending appointment. Would you like to:
1. Schedule for another time
2. Speak with our staff
3. Just cancel"""
        
        return "No problem. Is there anything else you'd like to know about our services?"

    def handle_prescription_request(self, user_id, medication_name=None):
        """Handle prescription-related requests"""
        try:
            if not medication_name:
                return self.get_user_prescriptions(user_id)
                
            conn = get_db()
            cursor = conn.cursor()
            
            # Check if user has this prescription
            cursor.execute("""
                SELECT * FROM prescriptions 
                WHERE user_id = ? 
                AND medication_name LIKE ? 
                AND status = 'active'
                AND (end_date IS NULL OR date(end_date) >= date('now'))
            """, (user_id, f"%{medication_name}%"))
            
            prescription = cursor.fetchone()
            
            if not prescription:
                return f"I couldn't find an active prescription for {medication_name}. Please verify the medication name or contact your doctor."
            
            if prescription['refills_remaining'] <= 0:
                return f"You have no refills remaining for {prescription['medication_name']}. Please contact your doctor for a new prescription."
            
            response = f"📋 Prescription Details for {prescription['medication_name']}:\n\n"
            response += f"💊 Dosage: {prescription['dosage']}\n"
            response += f"⏰ Frequency: {prescription['frequency']}\n"
            response += f"🔄 Refills Remaining: {prescription['refills_remaining']}\n"
            
            if prescription['end_date']:
                response += f"📅 Valid until: {prescription['end_date']}\n\n"
            
            response += "Would you like to:\n"
            response += "1. Request a refill\n"
            response += "2. See usage instructions\n"
            response += "3. Contact your doctor\n"
            
            return response
            
        except Exception as e:
            print(f"Error handling prescription request: {str(e)}")
            return "Sorry, I couldn't process your prescription request at this moment."
        finally:
            if 'conn' in locals():
                conn.close()

    def handle_account_deactivation_request(self, user_id):
        """Handle account deactivation requests through chat"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Verify user exists and is active
            cursor.execute("SELECT status FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return "Unable to find your account."
            
            if user['status'] == 'deactivated':
                return "Your account is already deactivated."
            
            # Update user status
            cursor.execute("""
                UPDATE users 
                SET status = 'deactivated' 
                WHERE id = ?
            """, (user_id,))
            
            conn.commit()
            
            # Clear session
            from flask import session
            session.clear()
            
            return {
                "message": "Your account has been deactivated. You will be logged out automatically. If you wish to reactivate your account in the future, please contact our support team.",
                "action": "logout"
            }
            
        except Exception as e:
            print(f"Error in account deactivation request: {str(e)}")
            return "I'm having trouble understanding. Could you please try again?"
        finally:
            if 'conn' in locals():
                conn.close()

    def handle_appointment_request(self, doctor_name, appointment_time):
        """Handle appointment scheduling request"""
        try:
            response = f"✅ Great! Let me confirm your appointment details:\n\n"
            response += f"👨‍⚕️ Doctor: Dr. {doctor_name}\n"
            response += f"📅 Date: [tomorrow's date]\n"
            response += f"⏰ Time: {appointment_time}\n"
            response += f"📋 Type: General Checkup\n"
            response += f"💵 Cost: $150.00\n\n"
            response += "Would you like me to proceed with booking this appointment?"
            return response
        except Exception as e:
            print(f"Error handling appointment request: {str(e)}")
            return "I'm having trouble understanding. Could you please try again?"

    def confirm_appointment(self, doctor_name, appointment_time):
        """Confirm appointment booking"""
        try:
            response = "✅ Your appointment has been confirmed!\n\n"
            response += "Appointment details have been sent to your email.\n"
            response += "Would you like me to:\n"
            response += "1. Set a reminder\n"
            response += "2. Add it to your calendar\n"
            response += "3. View appointment details"
            return response
        except Exception as e:
            print(f"Error confirming appointment: {str(e)}")
            return "I'm having trouble understanding. Could you please try again?"
