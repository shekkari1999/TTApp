"""
TTApp - School Timetable Management System
Main Flask Application

This application manages school timetables, teacher schedules, and handles
substitution for absent teachers.
"""

from flask import Flask, render_template, jsonify, request
from models import db, Teacher, Subject, Class, Schedule, Absence
from datetime import datetime, date, timedelta
import os
from dotenv import load_dotenv
import random

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Database configuration - PostgreSQL
# Get database URL from environment variable or use default
database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/ttapp')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize database
db.init_app(app)

# Create database tables
with app.app_context():
    db.create_all()


@app.route('/')
def index():
    """
    Main page route - renders the home page with initial UI.
    """
    return render_template('index.html')


@app.route('/admin')
def admin():
    """
    Admin setup page - for initial school configuration.
    """
    return render_template('admin.html')


@app.route('/api/generate-schedule', methods=['POST'])
def generate_schedule():
    """
    Generate initial schedule for all teachers.
    
    This endpoint:
    1. Clears existing schedules
    2. Generates a new schedule based on:
       - Number of classes
       - Number of subjects
       - Number of teachers
       - Class teacher assignments
    3. Assigns periods to teachers avoiding conflicts
    
    Returns JSON response with success status and message.
    """
    try:
        # Get configuration from request
        data = request.get_json() or {}
        num_classes = data.get('num_classes', 5)
        num_subjects = data.get('num_subjects', 7)
        periods_per_day = data.get('periods_per_day', 8)
        
        # Clear existing schedules
        Schedule.query.delete()
        db.session.commit()
        
        # Get all teachers (excluding leisure teachers)
        teachers = Teacher.query.filter_by(is_leisure=False).all()
        classes = Class.query.all()
        subjects = Subject.query.all()
        
        if not teachers or not classes or not subjects:
            return jsonify({
                'success': False,
                'message': 'Please add teachers, classes, and subjects first in the configuration.'
            }), 400
        
        # Ensure we have enough teachers and subjects
        # Note: We need at least 1 non-leisure teacher (teachers can teach multiple classes)
        if len(teachers) < 1:
            return jsonify({
                'success': False,
                'message': 'Need at least 1 non-leisure teacher to generate schedules.'
            }), 400
        
        # Note: No minimum subject requirement - will use available subjects
        
        # Generate schedule for each day of the week (Monday=0 to Sunday=6)
        # We'll generate for Monday-Friday (0-4)
        for day in range(5):  # Monday to Friday
            # Assign class teachers to first period of their classes
            for class_obj in classes:
                if class_obj.class_teacher_id:
                    class_teacher = Teacher.query.get(class_obj.class_teacher_id)
                    if class_teacher and not class_teacher.is_leisure:
                        # Assign first period to class teacher
                        schedule = Schedule(
                            teacher_id=class_teacher.id,
                            class_id=class_obj.id,
                            subject_id=subjects[0].id,  # First subject
                            day=day,
                            period=1
                        )
                        db.session.add(schedule)
            
            # Assign remaining periods
            for period in range(2, periods_per_day + 1):
                for class_obj in classes:
                    # Get available teachers (not already assigned this period, not leisure)
                    assigned_teachers = [
                        s.teacher_id for s in Schedule.query.filter_by(
                            day=day, period=period
                        ).all()
                    ]
                    
                    available_teachers = [
                        t for t in teachers 
                        if t.id not in assigned_teachers
                    ]
                    
                    # If no available teachers, reuse teachers (allow same teacher for multiple classes)
                    if not available_teachers:
                        available_teachers = teachers
                    
                    if available_teachers and subjects:
                        # Randomly select a teacher
                        teacher = random.choice(available_teachers)
                        # Randomly select a subject
                        subject = random.choice(subjects)
                        
                        schedule = Schedule(
                            teacher_id=teacher.id,
                            class_id=class_obj.id,
                            subject_id=subject.id,
                            day=day,
                            period=period
                        )
                        db.session.add(schedule)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Schedule generated successfully for {num_classes} classes, {num_subjects} subjects, and {len(teachers)} teachers.'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error generating schedule: {str(e)}'
        }), 500


@app.route('/api/absent-teachers', methods=['GET', 'POST'])
def absent_teachers():
    """
    Handle absent teachers - GET shows absences, POST marks a teacher as absent.
    
    GET: Returns list of absent teachers and available substitutes for a given date.
    POST: Marks a teacher as absent for a specific date.
    
    Query params (GET):
        date: Date in YYYY-MM-DD format (defaults to today)
    
    Request body (POST):
        teacher_id: ID of absent teacher
        date: Date in YYYY-MM-DD format
    """
    if request.method == 'GET':
        # Get date from query parameter or use today
        date_str = request.args.get('date', date.today().isoformat())
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid date format. Use YYYY-MM-DD.'
            }), 400
        
        # Get day of week (0=Monday, 6=Sunday)
        day_of_week = target_date.weekday()
        
        # Get all absences for this date
        absences = Absence.query.filter_by(date=target_date).all()
        
        # Get all teachers
        all_teachers = Teacher.query.all()
        
        # For each absence, find available substitutes
        result = []
        for absence in absences:
            absent_teacher = Teacher.query.get(absence.teacher_id)
            
            # Get schedules of absent teacher for this day
            absent_schedules = Schedule.query.filter_by(
                teacher_id=absence.teacher_id,
                day=day_of_week
            ).all()
            
            # Find available substitutes (non-leisure teachers who are not absent)
            absent_teacher_ids = [a.teacher_id for a in absences]
            available_substitutes = [
                t for t in all_teachers
                if not t.is_leisure
                and t.id != absence.teacher_id
                and t.id not in absent_teacher_ids
            ]
            
            # For each class the absent teacher teaches, find substitutes
            substitution_suggestions = []
            for schedule in absent_schedules:
                # Find teachers who don't have a class at this period
                busy_teachers = [
                    s.teacher_id for s in Schedule.query.filter_by(
                        day=day_of_week,
                        period=schedule.period
                    ).all()
                ]
                
                potential_substitutes = [
                    t for t in available_substitutes
                    if t.id not in busy_teachers
                ]
                
                substitution_suggestions.append({
                    'class_id': schedule.class_id,
                    'class_name': Class.query.get(schedule.class_id).name if Class.query.get(schedule.class_id) else 'Unknown',
                    'period': schedule.period,
                    'subject_id': schedule.subject_id,
                    'subject_name': Subject.query.get(schedule.subject_id).name if Subject.query.get(schedule.subject_id) else 'Unknown',
                    'available_substitutes': [t.to_dict() for t in potential_substitutes[:2]]  # Top 2 suggestions
                })
            
            result.append({
                'absence_id': absence.id,
                'teacher': absent_teacher.to_dict() if absent_teacher else None,
                'date': absence.date.isoformat(),
                'is_substituted': absence.is_substituted,
                'substitution_suggestions': substitution_suggestions
            })
        
        return jsonify({
            'success': True,
            'date': target_date.isoformat(),
            'absences': result
        })
    
    elif request.method == 'POST':
        # Mark a teacher as absent
        data = request.get_json()
        teacher_id = data.get('teacher_id')
        date_str = data.get('date', date.today().isoformat())
        
        if not teacher_id:
            return jsonify({
                'success': False,
                'message': 'teacher_id is required'
            }), 400
        
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid date format. Use YYYY-MM-DD.'
            }), 400
        
        # Check if absence already exists
        existing = Absence.query.filter_by(
            teacher_id=teacher_id,
            date=target_date
        ).first()
        
        if existing:
            return jsonify({
                'success': False,
                'message': 'Teacher is already marked as absent for this date.'
            }), 400
        
        # Create new absence
        absence = Absence(
            teacher_id=teacher_id,
            date=target_date,
            is_substituted=False
        )
        
        db.session.add(absence)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Teacher marked as absent successfully.',
            'absence': absence.to_dict()
        })


@app.route('/api/teachers', methods=['GET', 'POST'])
def teachers():
    """Get all teachers or create a new teacher."""
    if request.method == 'GET':
        teachers_list = Teacher.query.all()
        return jsonify({
            'success': True,
            'teachers': [t.to_dict() for t in teachers_list]
        })
    elif request.method == 'POST':
        data = request.get_json()
        teacher = Teacher(
            name=data.get('name'),
            is_class_teacher=data.get('is_class_teacher', False),
            is_leisure=data.get('is_leisure', False)
        )
        db.session.add(teacher)
        db.session.commit()
        return jsonify({
            'success': True,
            'teacher': teacher.to_dict()
        })


@app.route('/api/teachers/<int:teacher_id>', methods=['PUT', 'DELETE'])
def teacher_detail(teacher_id):
    """Update or delete a specific teacher."""
    teacher = Teacher.query.get_or_404(teacher_id)
    
    if request.method == 'PUT':
        data = request.get_json()
        teacher.name = data.get('name', teacher.name)
        teacher.is_class_teacher = data.get('is_class_teacher', teacher.is_class_teacher)
        teacher.is_leisure = data.get('is_leisure', teacher.is_leisure)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Teacher updated successfully.',
            'teacher': teacher.to_dict()
        })
    
    elif request.method == 'DELETE':
        db.session.delete(teacher)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Teacher deleted successfully.'
        })


@app.route('/api/subjects', methods=['GET', 'POST'])
def subjects():
    """Get all subjects or create a new subject."""
    if request.method == 'GET':
        subjects_list = Subject.query.all()
        return jsonify({
            'success': True,
            'subjects': [s.to_dict() for s in subjects_list]
        })
    elif request.method == 'POST':
        data = request.get_json()
        subject = Subject(name=data.get('name'))
        db.session.add(subject)
        db.session.commit()
        return jsonify({
            'success': True,
            'subject': subject.to_dict()
        })


@app.route('/api/subjects/<int:subject_id>', methods=['PUT', 'DELETE'])
def subject_detail(subject_id):
    """Update or delete a specific subject."""
    subject = Subject.query.get_or_404(subject_id)
    
    if request.method == 'PUT':
        data = request.get_json()
        subject.name = data.get('name', subject.name)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Subject updated successfully.',
            'subject': subject.to_dict()
        })
    
    elif request.method == 'DELETE':
        db.session.delete(subject)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Subject deleted successfully.'
        })


@app.route('/api/classes', methods=['GET', 'POST'])
def classes():
    """Get all classes or create a new class."""
    if request.method == 'GET':
        classes_list = Class.query.all()
        return jsonify({
            'success': True,
            'classes': [c.to_dict() for c in classes_list]
        })
    elif request.method == 'POST':
        data = request.get_json()
        class_obj = Class(
            name=data.get('name'),
            class_teacher_id=data.get('class_teacher_id')
        )
        db.session.add(class_obj)
        db.session.commit()
        return jsonify({
            'success': True,
            'class': class_obj.to_dict()
        })


@app.route('/api/classes/<int:class_id>', methods=['PUT', 'DELETE'])
def class_detail(class_id):
    """Update or delete a specific class."""
    class_obj = Class.query.get_or_404(class_id)
    
    if request.method == 'PUT':
        data = request.get_json()
        class_obj.name = data.get('name', class_obj.name)
        class_obj.class_teacher_id = data.get('class_teacher_id', class_obj.class_teacher_id)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Class updated successfully.',
            'class': class_obj.to_dict()
        })
    
    elif request.method == 'DELETE':
        db.session.delete(class_obj)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Class deleted successfully.'
        })


@app.route('/api/teacher-timetable/<int:teacher_id>', methods=['GET'])
def teacher_timetable(teacher_id):
    """
    Generate and return timetable for a specific teacher.
    
    Query params:
        date: Optional date in YYYY-MM-DD format (defaults to today)
    """
    teacher = Teacher.query.get_or_404(teacher_id)
    
    # Get date from query parameter or use today
    date_str = request.args.get('date', date.today().isoformat())
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({
            'success': False,
            'message': 'Invalid date format. Use YYYY-MM-DD.'
        }), 400
    
    # Get day of week (0=Monday, 6=Sunday)
    day_of_week = target_date.weekday()
    
    # Check if it's a weekend (Saturday=5, Sunday=6)
    if day_of_week >= 5:
        return jsonify({
            'success': True,
            'teacher': teacher.to_dict(),
            'date': target_date.isoformat(),
            'day_name': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day_of_week],
            'timetable': [],
            'message': 'Schedules are only generated for weekdays (Monday-Friday).'
        })
    
    # Get all schedules for this teacher on this day
    schedules = Schedule.query.filter_by(
        teacher_id=teacher_id,
        day=day_of_week
    ).order_by(Schedule.period).all()
    
    # Format schedule data
    timetable = []
    for schedule in schedules:
        class_obj = Class.query.get(schedule.class_id)
        subject = Subject.query.get(schedule.subject_id)
        
        timetable.append({
            'period': schedule.period,
            'class_name': class_obj.name if class_obj else 'Unknown',
            'subject_name': subject.name if subject else 'Unknown',
            'class_id': schedule.class_id,
            'subject_id': schedule.subject_id
        })
    
    return jsonify({
        'success': True,
        'teacher': teacher.to_dict(),
        'date': target_date.isoformat(),
        'day_name': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day_of_week],
        'timetable': timetable
    })


if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)

