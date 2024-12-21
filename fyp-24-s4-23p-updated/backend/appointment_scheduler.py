from db_connection import get_db
from datetime import datetime, timedelta
import json

class AppointmentScheduler:
    @staticmethod
    def schedule_appointment(user_id, doctor_name, appointment_date, appointment_type, appointment_time):
        """Schedule a new appointment"""
        try:
            # Convert date string to proper format if needed
            if isinstance(appointment_date, str) and appointment_date.lower() == 'tomorrow':
                appointment_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Capitalize doctor name properly
            doctor_name = doctor_name.title()
            
            print(f"Scheduling appointment for user {user_id} with Dr. {doctor_name}")
            print(f"Date: {appointment_date}, Time: {appointment_time}")
            
            conn = get_db()
            cursor = conn.cursor()
            
            # Check if doctor exists and is active
            cursor.execute("""
                SELECT * FROM doctors 
                WHERE name = ? AND status = 'active'
            """, (doctor_name,))
            doctor = cursor.fetchone()
            
            if not doctor:
                print(f"Doctor {doctor_name} not found or not active")
                return None
            
            # Check if slot is within doctor's schedule
            day_of_week = datetime.strptime(appointment_date, '%Y-%m-%d').strftime('%A').lower()
            schedule = json.loads(doctor['schedule'])
            
            if day_of_week not in schedule:
                print(f"Doctor {doctor_name} does not work on {day_of_week}")
                return None
            
            work_hours = schedule[day_of_week].split('-')
            work_start = datetime.strptime(work_hours[0], '%H:%M').time()
            work_end = datetime.strptime(work_hours[1], '%H:%M').time()
            appointment_time_obj = datetime.strptime(appointment_time, '%H:%M').time()
            
            if appointment_time_obj < work_start or appointment_time_obj > work_end:
                print(f"Appointment time {appointment_time} is outside doctor's working hours")
                return None
            
            # Check if slot is available
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM appointments 
                WHERE doctor_name = ? 
                AND appointment_date = ? 
                AND appointment_time = ? 
                AND status != 'cancelled'
            """, (doctor_name, appointment_date, appointment_time))
            
            if cursor.fetchone()['count'] > 0:
                print(f"Slot {appointment_time} is already booked")
                return None
            
            # Insert the appointment
            cursor.execute("""
                INSERT INTO appointments 
                (user_id, doctor_name, appointment_date, appointment_time, appointment_type, status)
                VALUES (?, ?, ?, ?, ?, 'scheduled')
            """, (user_id, doctor_name, appointment_date, appointment_time, appointment_type))
            
            appointment_id = cursor.lastrowid
            
            # Create a bill for the appointment
            amount = 150.00 if appointment_type == 'General Checkup' else 200.00
            cursor.execute("""
                INSERT INTO bills 
                (user_id, appointment_id, amount, description, status, due_date)
                VALUES (?, ?, ?, ?, 'PENDING', date(?, '+30 days'))
            """, (user_id, appointment_id, amount, f"{appointment_type} Appointment", appointment_date))
            
            conn.commit()
            print(f"Appointment scheduled successfully with ID: {appointment_id}")
            return appointment_id
            
        except Exception as e:
            print(f"Error scheduling appointment: {str(e)}")
            if 'conn' in locals():
                conn.rollback()
            return None
        finally:
            if 'conn' in locals():
                conn.close()

    @staticmethod
    def cancel_appointment(appointment_id, user_id):
        """Cancel an appointment"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE appointments 
                SET status = 'cancelled' 
                WHERE id = ? AND user_id = ?
            """, (appointment_id, user_id))
            
            if cursor.rowcount > 0:
                cursor.execute("""
                    UPDATE bills 
                    SET status = 'CANCELLED' 
                    WHERE appointment_id = ?
                """, (appointment_id,))
                conn.commit()
                return True
            return False
        except Exception as e:
            print(f"Error cancelling appointment: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()

    @staticmethod
    def reschedule_appointment(appointment_id, user_id, new_date, new_time):
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            # Verify appointment belongs to user
            cursor.execute("""
                SELECT * FROM appointments 
                WHERE id = ? AND user_id = ? AND status != 'cancelled'
            """, (appointment_id, user_id))
            appointment = cursor.fetchone()
            
            if not appointment:
                return False
            
            # Validate new time is during clinic hours
            time_obj = datetime.strptime(new_time, '%H:%M').time()
            if time_obj.hour < 8 or time_obj.hour > 18:
                return False
            
            # Check if new slot is available
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM appointments 
                WHERE appointment_date = ? AND appointment_time = ? AND status != 'cancelled'
            """, (new_date, new_time))
            result = cursor.fetchone()
            
            if result['count'] > 0:
                return False
            
            # Reschedule the appointment
            cursor.execute("""
                UPDATE appointments 
                SET appointment_date = ?,
                    appointment_time = ?,
                    status = 'rescheduled',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_date, new_time, appointment_id))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error rescheduling appointment: {str(e)}")
            conn.rollback()
            return False
        finally:
            conn.close()

    @staticmethod
    def get_available_slots(date):
        """Get available appointment slots for a given date"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Convert date string to proper format if needed
            if isinstance(date, str) and date.lower() == 'tomorrow':
                date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Get all doctors
            cursor.execute("SELECT * FROM doctors WHERE status = 'active'")
            doctors = cursor.fetchall()
            
            # Get booked slots
            cursor.execute("""
                SELECT appointment_time, doctor_name 
                FROM appointments 
                WHERE appointment_date = ? AND status != 'cancelled'
            """, (date,))
            booked_slots = cursor.fetchall()
            
            # Generate available slots (9 AM to 5 PM, 30-minute intervals)
            available_slots = []
            for doctor in doctors:
                doctor_name = doctor['name']
                schedule = json.loads(doctor['schedule'])
                
                # Get day of week for the date
                day_of_week = datetime.strptime(date, '%Y-%m-%d').strftime('%A').lower()
                
                if day_of_week in schedule:
                    work_hours = schedule[day_of_week].split('-')
                    start_time = datetime.strptime(work_hours[0], '%H:%M')
                    end_time = datetime.strptime(work_hours[1], '%H:%M')
                    
                    current_slot = start_time
                    while current_slot < end_time:
                        slot_time = current_slot.strftime('%H:%M')
                        # Check if slot is not booked for this doctor
                        if not any(b['appointment_time'] == slot_time and b['doctor_name'] == doctor_name for b in booked_slots):
                            available_slots.append({
                                'time': slot_time,
                                'doctor': doctor_name
                            })
                        current_slot += timedelta(minutes=30)
            
            return available_slots
        except Exception as e:
            print(f"Error getting available slots: {str(e)}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()

    @staticmethod
    def get_appointment_details(appointment_id):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT a.*, u.email, u.phone
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            WHERE a.id = ?
        """, (appointment_id,))
        appointment = cursor.fetchone()
        conn.close()
        return appointment

    @staticmethod
    def get_available_doctors(date=None, time=None):
        """Get list of available doctors"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            # Get all active doctors
            cursor.execute("""
                SELECT DISTINCT doctor_name 
                FROM appointments 
                WHERE status != 'cancelled'
                UNION
                SELECT 'Smith' as doctor_name
                UNION
                SELECT 'Johnson' as doctor_name
                UNION
                SELECT 'Williams' as doctor_name
            """)
            
            doctors = cursor.fetchall()
            return [{'name': doc['doctor_name'], 'speciality': 'General Practice'} for doc in doctors]
        except Exception as e:
            print(f"Error getting available doctors: {str(e)}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()

    @staticmethod
    def get_next_available_slots(days=7):
        """Get next available appointment slots for the next X days"""
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            available_slots = []
            current_date = datetime.now().date()
            
            for i in range(days):
                check_date = current_date + timedelta(days=i)
                if check_date.weekday() < 7:  # Monday to Sunday
                    # Get booked slots for this date
                    cursor.execute("""
                        SELECT appointment_time, doctor_id 
                        FROM appointments 
                        WHERE appointment_date = ? 
                        AND status != 'cancelled'
                    """, (check_date.strftime('%Y-%m-%d'),))
                    booked_slots = cursor.fetchall()
                    
                    # Get all doctors
                    cursor.execute("SELECT * FROM doctors WHERE status = 'active'")
                    doctors = cursor.fetchall()
                    
                    # Generate available slots
                    for hour in range(8, 18):  # 8 AM to 6 PM
                        time_slot = f"{hour:02d}:00"
                        for doctor in doctors:
                            if not any(b['appointment_time'] == time_slot and b['doctor_id'] == doctor['id'] for b in booked_slots):
                                available_slots.append({
                                    'date': check_date.strftime('%Y-%m-%d'),
                                    'time': time_slot,
                                    'doctor': doctor['name']
                                })
            
            return available_slots
            
        except Exception as e:
            print(f"Error getting next available slots: {str(e)}")
            return []
        finally:
            conn.close()

    @staticmethod
    def confirm_appointment(appointment_id):
        """Confirm a scheduled appointment"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE appointments 
                SET status = 'confirmed' 
                WHERE id = ? AND status = 'scheduled'
            """, (appointment_id,))
            
            success = cursor.rowcount > 0
            if success:
                conn.commit()
            return success
        except Exception as e:
            print(f"Error confirming appointment: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
