from flask import Flask, render_template, request, jsonify, redirect, url_for
# Reverted import back to standard
from models import init_db, Company, TechStack, CurriculumUnit, UserProgress, get_db_connection 
import os
import json
from datetime import datetime, date # Added date import
from collections import defaultdict # Import defaultdict for easier grouping

app = Flask(__name__)

# Ensure the database directory exists
# The path needs to be relative to the app.py file now
db_dir = os.path.join(os.path.dirname(__file__), 'database')
os.makedirs(db_dir, exist_ok=True)

# Initialize the database
init_db()

@app.route('/')
def index():
    """Render the home page."""
    # Get today's schedule across all companies
    today_schedule = CurriculumUnit.get_overall_today_schedule()
    return render_template('index.html', today_schedule=today_schedule)

@app.route('/schedule')
def schedule():
    """Render the full schedule page, allowing company selection."""
    companies = Company.get_all()
    selected_company_id = request.args.get('company_id', type=int)
    schedule_data_by_month = defaultdict(lambda: defaultdict(list)) # Grouped by month, then formatted date
    today_str = date.today().strftime('%Y-%m-%d') # Get today's date string for highlighting

    company_schedule_exists = False
    if selected_company_id:
        # Fetch the raw schedule data (keys are 'YYYY-MM-DD')
        raw_schedule_data = CurriculumUnit.get_schedule_for_company(selected_company_id)
        if raw_schedule_data:
            company_schedule_exists = True
            # Sort the raw data by date string keys
            sorted_dates = sorted(raw_schedule_data.keys())
            # Group by month and format dates
            for dt_str in sorted_dates:
                items = raw_schedule_data[dt_str]
                try:
                    dt_obj = datetime.strptime(dt_str, '%Y-%m-%d').date()
                    month_year_key = dt_obj.strftime('%Y-%m') # Key for grouping by month
                    formatted_date_key = dt_obj.strftime('%A, %B %d, %Y') # Key for display
                    # Add original date string to items for comparison in template
                    for item in items:
                        item['schedule_date_str'] = dt_str 
                    schedule_data_by_month[month_year_key][formatted_date_key].extend(items)
                except ValueError:
                     # Handle potential formatting errors if needed, though unlikely with sorted keys
                     pass 

    elif companies:
        # Default to the first company if none selected but companies exist
        selected_company_id = companies[0]['id']
        raw_schedule_data = CurriculumUnit.get_schedule_for_company(selected_company_id)
        if raw_schedule_data:
            company_schedule_exists = True
            sorted_dates = sorted(raw_schedule_data.keys())
            for dt_str in sorted_dates:
                items = raw_schedule_data[dt_str]
                try:
                    dt_obj = datetime.strptime(dt_str, '%Y-%m-%d').date()
                    month_year_key = dt_obj.strftime('%Y-%m')
                    formatted_date_key = dt_obj.strftime('%A, %B %d, %Y') 
                    for item in items:
                        item['schedule_date_str'] = dt_str
                    schedule_data_by_month[month_year_key][formatted_date_key].extend(items)
                except ValueError:
                     pass
        
    # Sort the months dictionary by key (YYYY-MM)
    sorted_schedule_data_by_month = dict(sorted(schedule_data_by_month.items()))

    return render_template('schedule.html', 
                           schedule_by_month=sorted_schedule_data_by_month, # Pass grouped and sorted schedule
                           companies=companies, 
                           selected_company_id=selected_company_id,
                           today_str=today_str, # Pass today's date string
                           company_schedule_exists=company_schedule_exists) # Flag if schedule exists

@app.route('/companies')
def companies():
    """Render the companies management page."""
    all_companies = Company.get_all()
    # Fetch tech stack templates for the dropdown
    tech_stack_templates = TechStack.get_all_templates() 
    return render_template('companies.html', companies=all_companies, tech_stack_templates=tech_stack_templates)

@app.route('/companies/add', methods=['POST'])
def add_company():
    """Add a new company and associate selected tech stacks."""
    name = request.form.get('name')
    description = request.form.get('description', '')
    # Get list of selected tech stack template IDs
    tech_stack_ids = request.form.getlist('tech_stack_ids') 
    
    if name:
        company_id = Company.create(name, description)
        if company_id and tech_stack_ids:
            for ts_id in tech_stack_ids:
                try:
                    Company.add_tech_stack(company_id, int(ts_id))
                except ValueError:
                    print(f"Invalid tech_stack_id: {ts_id}") # Log error
                    continue # Skip invalid IDs
    
    return redirect(url_for('companies'))

@app.route('/companies/<int:company_id>')
def company_detail(company_id):
    """Render the company detail page."""
    company = Company.get_by_id(company_id)
    if not company:
        return "Company not found", 404
        
    # Get tech stacks specifically associated with this company
    associated_tech_stacks = Company.get_tech_stacks(company_id) 
    # Get all available tech stack templates to add more
    tech_stack_templates = TechStack.get_all_templates() 
    
    # Get progress data for this company to display
    progress_data = UserProgress.get_progress_for_company(company_id)
    
    return render_template('company_detail.html', 
                           company=company, 
                           associated_tech_stacks=associated_tech_stacks,
                           tech_stack_templates=tech_stack_templates,
                           progress_data=progress_data) # Pass progress data

@app.route('/companies/<int:company_id>/tech_stacks/add', methods=['POST'])
def add_tech_stack_to_company(company_id):
    """Associate a tech stack template with a company."""
    tech_stack_id = request.form.get('tech_stack_id')
    if tech_stack_id:
        try:
            Company.add_tech_stack(company_id, int(tech_stack_id))
        except ValueError:
             print(f"Invalid tech_stack_id: {tech_stack_id}") # Log error
    return redirect(url_for('company_detail', company_id=company_id))

# --- Routes for managing Tech Stack Templates ---
@app.route('/tech_stack_templates')
def tech_stack_templates():
    """Render page to manage tech stack templates."""
    templates = TechStack.get_all_templates()
    return render_template('tech_stack_templates.html', templates=templates)

@app.route('/tech_stack_templates/add', methods=['POST'])
def add_tech_stack_template():
    """Add a new tech stack template."""
    name = request.form.get('name')
    description = request.form.get('description', '')
    if name:
        TechStack.create_template(name, description)
    return redirect(url_for('tech_stack_templates'))

@app.route('/tech_stack_templates/<int:template_id>')
def tech_stack_template_detail(template_id):
    """Render detail page for a tech stack template."""
    template = TechStack.get_by_id(template_id)
    if not template:
        return "Template not found", 404
    units = CurriculumUnit.get_by_tech_stack(template_id)
    return render_template('tech_stack_template_detail.html', template=template, units=units)

@app.route('/tech_stack_templates/<int:template_id>/units/add', methods=['POST'])
def add_unit_to_template(template_id):
    """Add a new curriculum unit to a tech stack template."""
    title = request.form.get('title')
    description = request.form.get('description', '')
    order_index = int(request.form.get('order_index', 0))
    duration_days = int(request.form.get('duration_days', 1))
    
    if title:
        CurriculumUnit.create(template_id, title, description, order_index, duration_days)
    
    return redirect(url_for('tech_stack_template_detail', template_id=template_id))

# --- Progress Marking ---
# Updated routes to use company_tech_stack_id and curriculum_unit_id
@app.route('/progress/mark_completed/<int:company_tech_stack_id>/<int:unit_id>', methods=['POST'])
def mark_completed(company_tech_stack_id, unit_id):
    """Mark a curriculum unit as completed for a specific company context."""
    UserProgress.mark_completed(company_tech_stack_id, unit_id)
    # Redirect back to the page the user was on, default to index
    return redirect(request.referrer or url_for('index')) 

@app.route('/progress/mark_incomplete/<int:company_tech_stack_id>/<int:unit_id>', methods=['POST'])
def mark_incomplete(company_tech_stack_id, unit_id):
    """Mark a curriculum unit as incomplete for a specific company context."""
    UserProgress.mark_incomplete(company_tech_stack_id, unit_id)
    return redirect(request.referrer or url_for('index'))

# --- API Routes (Refactored) ---
@app.route('/api/companies', methods=['GET'])
def api_companies():
    """API endpoint to get all companies."""
    companies = Company.get_all()
    return jsonify([dict(company) for company in companies])

@app.route('/api/companies/<int:company_id>/tech_stacks', methods=['GET'])
def api_company_tech_stacks(company_id):
    """API endpoint to get tech stacks associated with a company."""
    tech_stacks = Company.get_tech_stacks(company_id)
    return jsonify([dict(ts) for ts in tech_stacks])

@app.route('/api/tech_stack_templates/<int:template_id>/units', methods=['GET'])
def api_template_units(template_id):
    """API endpoint to get all curriculum units for a tech stack template."""
    units = CurriculumUnit.get_by_tech_stack(template_id)
    return jsonify([dict(unit) for unit in units])

@app.route('/api/companies/<int:company_id>/schedule', methods=['GET'])
def api_company_schedule(company_id):
    """API endpoint to get the learning schedule for a company."""
    schedule = CurriculumUnit.get_schedule_for_company(company_id)
    # Convert date keys back to strings for JSON
    schedule_str_keys = {k.strftime('%Y-%m-%d'): v for k, v in schedule.items()}
    return jsonify(schedule_str_keys)

@app.route('/api/today_schedule', methods=['GET'])
def api_today_schedule():
    """API endpoint to get today's schedule across all companies."""
    today_schedule = CurriculumUnit.get_overall_today_schedule()
    return jsonify(today_schedule)

@app.route('/api/companies/<int:company_id>/progress', methods=['GET'])
def api_company_progress(company_id):
    """API endpoint to get progress for a company."""
    progress = UserProgress.get_progress_for_company(company_id)
    return jsonify([dict(item) for item in progress])

# --- Sample Data (Refactored) ---
def add_sample_data():
    """Add sample data to the database if it's empty."""
    conn = get_db_connection() # Use imported function
    # Check if templates exist first
    templates_exist = conn.execute("SELECT COUNT(*) as count FROM tech_stacks WHERE is_template = TRUE").fetchone()
    conn.close()

    if templates_exist is None or templates_exist['count'] == 0:
        print("Adding sample data...")
        # Add tech stack templates and their curriculum units
        react_template_id = TechStack.create_template("ReactJS", "Frontend JavaScript library")
        CurriculumUnit.create(react_template_id, "React Basics", "Learn the fundamentals of React", 0, 2)
        CurriculumUnit.create(react_template_id, "Components & Props", "Understanding components and props", 1, 3)
        CurriculumUnit.create(react_template_id, "State & Lifecycle", "Managing state and component lifecycle", 2, 4)
        CurriculumUnit.create(react_template_id, "Hooks", "Using React hooks", 3, 3)
        CurriculumUnit.create(react_template_id, "Routing", "Client-side routing with React Router", 4, 2)
        
        sql_template_id = TechStack.create_template("SQL", "Database query language")
        CurriculumUnit.create(sql_template_id, "SQL Basics", "Learn the fundamentals of SQL", 0, 2)
        CurriculumUnit.create(sql_template_id, "Queries & Joins", "Writing complex queries and joins", 1, 3)
        CurriculumUnit.create(sql_template_id, "Indexes & Optimization", "Optimizing database performance", 2, 4)
        
        python_template_id = TechStack.create_template("Python", "General-purpose programming language")
        CurriculumUnit.create(python_template_id, "Python Basics", "Learn the fundamentals of Python", 0, 2)
        CurriculumUnit.create(python_template_id, "Data Structures", "Lists, dictionaries, sets, and tuples", 1, 3)
        CurriculumUnit.create(python_template_id, "Functions & OOP", "Functions and object-oriented programming", 2, 4)
        CurriculumUnit.create(python_template_id, "Libraries & Frameworks", "Popular Python libraries and frameworks", 3, 5)

        # Add sample companies and associate tech stacks
        company_id_1 = Company.create("TechCorp", "A technology company")
        Company.add_tech_stack(company_id_1, react_template_id)
        Company.add_tech_stack(company_id_1, python_template_id)
        
        company_id_2 = Company.create("Data Inc.", "Data analysis services")
        Company.add_tech_stack(company_id_2, sql_template_id)
        Company.add_tech_stack(company_id_2, python_template_id)
        print("Sample data added.")
    else:
        print("Sample data already exists.")


if __name__ == '__main__':
    # Add sample data if needed
    try:
        # Import here specifically for the __main__ block execution
        from models import get_db_connection 
        add_sample_data()
    except Exception as e:
        print(f"Error adding sample data: {e}")
        # Optionally, re-initialize DB if sample data fails due to schema issues
        # print("Attempting to re-initialize database...")
        # init_db() 
        # add_sample_data() # Try again
    
    # Run the app
    app.run(debug=True)
