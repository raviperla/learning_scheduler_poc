from datetime import datetime, timedelta
import sqlite3
import json
import os

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'learning_tracker.db')

def get_db_connection():
    """Create a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with required tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Drop tables in reverse order of dependency
    cursor.execute("DROP TABLE IF EXISTS user_progress")
    cursor.execute("DROP TABLE IF EXISTS curriculum_units")
    cursor.execute("DROP TABLE IF EXISTS company_tech_stacks")
    cursor.execute("DROP TABLE IF EXISTS tech_stacks") 
    cursor.execute("DROP TABLE IF EXISTS companies")

    # Create TechStacks table (stores templates identified by is_template=TRUE)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tech_stacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        is_template BOOLEAN DEFAULT TRUE, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create CurriculumUnits table (linked to tech_stacks templates)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS curriculum_units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tech_stack_id INTEGER, 
        title TEXT NOT NULL,
        description TEXT,
        order_index INTEGER,
        duration_days INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tech_stack_id) REFERENCES tech_stacks (id) ON DELETE CASCADE 
    )
    ''')

    # Create Companies table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create CompanyTechStacks join table (Many-to-Many between companies and tech_stack templates)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS company_tech_stacks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER NOT NULL,
        tech_stack_id INTEGER NOT NULL, 
        start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE,
        FOREIGN KEY (tech_stack_id) REFERENCES tech_stacks (id) ON DELETE CASCADE,
        UNIQUE(company_id, tech_stack_id)
    )
    ''')

    # Create UserProgress table (links progress to a unit within a specific company's tech stack context)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_tech_stack_id INTEGER NOT NULL,
        curriculum_unit_id INTEGER NOT NULL,
        completed BOOLEAN DEFAULT FALSE,
        completion_date TIMESTAMP,
        FOREIGN KEY (company_tech_stack_id) REFERENCES company_tech_stacks (id) ON DELETE CASCADE,
        FOREIGN KEY (curriculum_unit_id) REFERENCES curriculum_units (id) ON DELETE CASCADE,
        UNIQUE(company_tech_stack_id, curriculum_unit_id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized (tables dropped and recreated).")

class Company:
    @staticmethod
    def create(name, description=""):
        """Create a new company."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO companies (name, description) VALUES (?, ?)",
            (name, description)
        )
        company_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return company_id

    @staticmethod
    def add_tech_stack(company_id, tech_stack_id):
        """Associate a tech stack template with a company."""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO company_tech_stacks (company_id, tech_stack_id) VALUES (?, ?)",
                (company_id, tech_stack_id)
            )
            conn.commit()
            print(f"Associated tech stack {tech_stack_id} with company {company_id}")
        except sqlite3.IntegrityError:
            print(f"Association between company {company_id} and tech stack {tech_stack_id} already exists.")
        except Exception as e:
            print(f"Error associating tech stack: {e}")
        finally:
            conn.close()

    @staticmethod
    def get_all():
        """Get all companies."""
        conn = get_db_connection()
        companies = conn.execute("SELECT * FROM companies").fetchall()
        conn.close()
        return companies
    
    @staticmethod
    def get_by_id(company_id):
        """Get a company by ID."""
        conn = get_db_connection()
        company = conn.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
        conn.close()
        return company

    @staticmethod
    def get_tech_stacks(company_id):
        """Get tech stacks associated with a company via the join table."""
        conn = get_db_connection()
        tech_stacks = conn.execute("""
            SELECT ts.*, cts.id as company_tech_stack_id, cts.start_date
            FROM tech_stacks ts
            JOIN company_tech_stacks cts ON ts.id = cts.tech_stack_id
            WHERE cts.company_id = ? AND ts.is_template = TRUE
        """, (company_id,)).fetchall()
        conn.close()
        return tech_stacks

class TechStack: # Represents Tech Stack Templates
    @staticmethod
    def create_template(name, description=""):
        """Create a new tech stack template."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tech_stacks (name, description, is_template) VALUES (?, ?, ?)",
            (name, description, True)
        )
        tech_stack_id = cursor.lastrowid
        conn.commit()
        conn.close()
        print(f"Created tech stack template: {name} (ID: {tech_stack_id})")
        return tech_stack_id
    
    @staticmethod
    def get_all_templates():
        """Get all tech stack templates."""
        conn = get_db_connection()
        templates = conn.execute("SELECT * FROM tech_stacks WHERE is_template = TRUE").fetchall()
        conn.close()
        return templates
    
    @staticmethod
    def get_by_id(tech_stack_id):
        """Get a tech stack template by ID."""
        conn = get_db_connection()
        tech_stack = conn.execute("SELECT * FROM tech_stacks WHERE id = ? AND is_template = TRUE", (tech_stack_id,)).fetchone()
        conn.close()
        return tech_stack

class CurriculumUnit: # Represents units belonging to a Tech Stack Template
    @staticmethod
    def create(tech_stack_id, title, description="", order_index=0, duration_days=1):
        """Create a new curriculum unit for a tech stack template."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO curriculum_units 
               (tech_stack_id, title, description, order_index, duration_days) 
               VALUES (?, ?, ?, ?, ?)""",
            (tech_stack_id, title, description, order_index, duration_days)
        )
        unit_id = cursor.lastrowid
        conn.commit()
        conn.close()
        print(f"Created curriculum unit '{title}' for tech stack {tech_stack_id}")
        return unit_id
    
    @staticmethod
    def get_by_tech_stack(tech_stack_id):
        """Get all curriculum units for a tech stack template."""
        conn = get_db_connection()
        units = conn.execute(
            "SELECT * FROM curriculum_units WHERE tech_stack_id = ? ORDER BY order_index",
            (tech_stack_id,)
        ).fetchall()
        conn.close()
        return units

    # --- Schedule Generation (Needs significant rework) ---
    @staticmethod
    def get_schedule_for_company(company_id):
        """
        Generate a learning schedule for a specific company based on its associated tech stacks.
        Handles parallel schedules starting from their association date.
        Returns a dictionary with dates as keys and lists of units as values.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get associated tech stacks and their start dates for the company
        cursor.execute("""
            SELECT cts.id as company_tech_stack_id, cts.tech_stack_id, cts.start_date, ts.name as tech_stack_name
            FROM company_tech_stacks cts
            JOIN tech_stacks ts ON cts.tech_stack_id = ts.id
            WHERE cts.company_id = ? AND ts.is_template = TRUE
        """, (company_id,))
        company_stacks = cursor.fetchall()

        schedule = {}
        company = Company.get_by_id(company_id)
        company_name = company['name'] if company else "Unknown Company"

        for cs in company_stacks:
            company_tech_stack_id = cs['company_tech_stack_id']
            tech_stack_id = cs['tech_stack_id']
            tech_stack_name = cs['tech_stack_name']
            # Parse the start date correctly
            try:
                 # Assuming start_date is stored like 'YYYY-MM-DD HH:MM:SS'
                start_dt = datetime.strptime(cs['start_date'], '%Y-%m-%d %H:%M:%S')
                start_date = start_dt.date()
            except (ValueError, TypeError):
                print(f"Warning: Could not parse start_date '{cs['start_date']}' for company_tech_stack_id {company_tech_stack_id}. Using today.")
                start_date = datetime.now().date() # Fallback to today

            current_schedule_date = start_date 

            # Get curriculum units for this tech stack template
            cursor.execute("""
                SELECT cu.id as curriculum_unit_id, cu.title, cu.description, cu.duration_days, cu.order_index,
                       up.completed
                FROM curriculum_units cu
                LEFT JOIN user_progress up ON cu.id = up.curriculum_unit_id AND up.company_tech_stack_id = ?
                WHERE cu.tech_stack_id = ?
                ORDER BY cu.order_index
            """, (company_tech_stack_id, tech_stack_id))
            units = cursor.fetchall()

            for unit in units:
                is_completed = bool(unit['completed']) if unit['completed'] is not None else False
                if not is_completed:
                    duration = unit['duration_days']
                    # Schedule each day of the unit
                    for i in range(duration):
                        schedule_date = current_schedule_date + timedelta(days=i)
                        date_str = schedule_date.strftime('%Y-%m-%d')
                        if date_str not in schedule:
                            schedule[date_str] = []
                        
                        # Check if this specific unit instance is already scheduled for this day
                        unit_already_scheduled = any(
                            item['curriculum_unit_id'] == unit['curriculum_unit_id'] and 
                            item['company_tech_stack_id'] == company_tech_stack_id 
                            for item in schedule[date_str]
                        )

                        if not unit_already_scheduled:
                            schedule[date_str].append({
                                'company_tech_stack_id': company_tech_stack_id,
                                'curriculum_unit_id': unit['curriculum_unit_id'],
                                'title': unit['title'],
                                'description': unit['description'],
                                'company_name': company_name,
                                'tech_stack_name': tech_stack_name,
                                'duration_days': duration,
                                'day_number': i + 1 # Track which day of the unit it is
                            })
                    
                    # Move current_schedule_date forward by the duration for the next unit in this stack
                    current_schedule_date += timedelta(days=duration)

        conn.close()
        # Sort the final schedule by date
        sorted_schedule = {k: schedule[k] for k in sorted(schedule)}
        return sorted_schedule

    @staticmethod
    def get_overall_today_schedule():
        """Get the schedule for today across all companies."""
        today = datetime.now().date()
        today_str = today.strftime('%Y-%m-%d')
        overall_today_schedule = []
        
        companies = Company.get_all()
        for company in companies:
            company_schedule = CurriculumUnit.get_schedule_for_company(company['id'])
            if today_str in company_schedule:
                overall_today_schedule.extend(company_schedule[today_str])
                
        # Optional: Sort combined schedule if needed, e.g., by company then tech stack
        overall_today_schedule.sort(key=lambda x: (x['company_name'], x['tech_stack_name'], x['title']))
        return overall_today_schedule


class UserProgress:
    @staticmethod
    def mark_completed(company_tech_stack_id, curriculum_unit_id):
        """Mark a curriculum unit as completed for a specific company's tech stack."""
        conn = get_db_connection()
        cursor = conn.cursor()
        completion_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Check if a record already exists
        existing = conn.execute(
            "SELECT id FROM user_progress WHERE company_tech_stack_id = ? AND curriculum_unit_id = ?", 
            (company_tech_stack_id, curriculum_unit_id)
        ).fetchone()
        
        if existing:
            cursor.execute(
                "UPDATE user_progress SET completed = ?, completion_date = ? WHERE id = ?",
                (True, completion_date, existing['id'])
            )
        else:
            cursor.execute(
                "INSERT INTO user_progress (company_tech_stack_id, curriculum_unit_id, completed, completion_date) VALUES (?, ?, ?, ?)",
                (company_tech_stack_id, curriculum_unit_id, True, completion_date)
            )
            
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    def mark_incomplete(company_tech_stack_id, curriculum_unit_id):
        """Mark a curriculum unit as incomplete for a specific company's tech stack."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update existing record if it exists, otherwise do nothing (or insert if needed, but update is safer)
        cursor.execute(
            "UPDATE user_progress SET completed = ?, completion_date = NULL WHERE company_tech_stack_id = ? AND curriculum_unit_id = ?",
            (False, company_tech_stack_id, curriculum_unit_id)
        )
            
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    def get_progress_for_company(company_id):
        """Get progress for all curriculum units for a specific company."""
        conn = get_db_connection()
        # This query needs adjustment to correctly reflect progress based on company_tech_stacks
        progress = conn.execute("""
            SELECT 
                cu.id as curriculum_unit_id, 
                cu.title, 
                ts.name as tech_stack_name, 
                c.name as company_name, 
                up.completed, 
                up.completion_date,
                cts.id as company_tech_stack_id
            FROM curriculum_units cu
            JOIN tech_stacks ts ON cu.tech_stack_id = ts.id
            JOIN company_tech_stacks cts ON ts.id = cts.tech_stack_id
            JOIN companies c ON cts.company_id = c.id
            LEFT JOIN user_progress up ON cu.id = up.curriculum_unit_id AND cts.id = up.company_tech_stack_id
            WHERE c.id = ?
            ORDER BY ts.name, cu.order_index
        """, (company_id,)).fetchall()
        conn.close()
        return progress
