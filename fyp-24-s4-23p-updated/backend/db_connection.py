import sqlite3
import os

def get_db():
    """Get a connection to the database"""
    db_path = os.path.join(os.path.dirname(__file__), 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Initialize the database with required tables"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                address TEXT,
                emergency_contact TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create doctors table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS doctors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                speciality TEXT NOT NULL,
                schedule TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create clinic_info table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clinic_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT NOT NULL,
                opening_hours TEXT NOT NULL,
                support_hours TEXT,
                map_link TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create clinic_services table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clinic_services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                duration INTEGER,
                price DECIMAL(10,2),
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create patient_profiles table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patient_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                first_name TEXT,
                last_name TEXT,
                date_of_birth TEXT,
                gender TEXT,
                blood_type TEXT,
                allergies TEXT,
                medical_conditions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Create appointments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                doctor_name TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                appointment_type TEXT NOT NULL,
                status TEXT DEFAULT 'scheduled',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Create bills table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                appointment_id INTEGER,
                amount DECIMAL(10,2) NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'PENDING',
                due_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (appointment_id) REFERENCES appointments (id)
            )
        """)
        
        # Create prescriptions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prescriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                medication_name TEXT NOT NULL,
                dosage TEXT NOT NULL,
                frequency TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                refills_remaining INTEGER DEFAULT 0,
                side_effects TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Create health_records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                record_type TEXT NOT NULL,
                record_date TEXT NOT NULL,
                description TEXT,
                doctor_notes TEXT,
                lab_results TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Create health_reminders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS health_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                reminder_type TEXT NOT NULL,
                reminder_date TEXT NOT NULL,
                reminder_time TEXT,
                description TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # Insert sample doctors if none exist
        cursor.execute("SELECT COUNT(*) as count FROM doctors")
        if cursor.fetchone()['count'] == 0:
            sample_doctors = [
                ('Smith', 'General Practice', '{"monday": "09:00-17:00", "tuesday": "09:00-17:00", "wednesday": "09:00-17:00", "thursday": "09:00-17:00", "friday": "09:00-17:00", "saturday": "09:00-17:00", "sunday": "09:00-17:00"}'),
                ('Johnson', 'Cardiology', '{"monday": "10:00-18:00", "tuesday": "10:00-18:00", "wednesday": "10:00-18:00", "thursday": "10:00-18:00", "friday": "10:00-18:00"}, "saturday": "09:00-17:00", "sunday": "09:00-17:00"'),
                ('Williams', 'Pediatrics', '{"monday": "08:00-16:00", "tuesday": "08:00-16:00", "wednesday": "08:00-16:00", "thursday": "08:00-16:00", "friday": "08:00-16:00"}, "saturday": "09:00-17:00", "sunday": "09:00-17:00"'),
                ('Davis', 'General Practice', '{"monday": "09:00-17:00", "wednesday": "09:00-17:00", "friday": "09:00-17:00"}, "saturday": "09:00-17:00", "sunday": "09:00-17:00"')
            ]
            
            cursor.executemany("""
                INSERT INTO doctors (name, speciality, schedule)
                VALUES (?, ?, ?)
            """, sample_doctors)
            
        # Insert clinic info if none exists
        cursor.execute("SELECT COUNT(*) as count FROM clinic_info")
        if cursor.fetchone()['count'] == 0:
            cursor.execute("""
                INSERT INTO clinic_info (
                    name, address, phone, email, opening_hours, support_hours, map_link
                ) VALUES (
                    'Healthcare Clinic',
                    '123 Medical Street, Healthcare City',
                    '1-800-HEALTH',
                    'contact@healthcareclinic.com',
                    'Monday-Sunday: 9:00 AM - 5:00 PM',
                    'Monday-Sunday: 8:00 AM - 6:00 PM',
                    'https://maps.google.com/?q=healthcare-clinic'
                )
            """)
            
        # Insert sample services if none exist
        cursor.execute("SELECT COUNT(*) as count FROM clinic_services")
        if cursor.fetchone()['count'] == 0:
            sample_services = [
                ('General Checkup', 'General', 'Comprehensive health examination', 30, 150.00),
                ('Specialist Consultation', 'Specialist', 'Consultation with specialist', 45, 200.00),
                ('Vaccination', 'Preventive', 'Various vaccinations available', 15, 100.00),
                ('Blood Test', 'Laboratory', 'Complete blood count and analysis', 20, 80.00)
            ]
            
            cursor.executemany("""
                INSERT INTO clinic_services (name, category, description, duration, price)
                VALUES (?, ?, ?, ?, ?)
            """, sample_services)
        
        conn.commit()
        print("Database initialized successfully")
        
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        conn.rollback()
    finally:
        conn.close()
