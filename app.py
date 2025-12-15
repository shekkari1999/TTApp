"""
TTApp - School Timetable Management System
Main Flask Application

This application manages school timetables, teacher schedules, and handles
substitution for absent teachers.
"""

from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from models import db, Teacher, Subject, Class, Schedule, Absence, User, TeacherUpdateRequest
from datetime import datetime, date, timedelta
from functools import wraps
import os
from dotenv import load_dotenv
import random
from sqlalchemy import func

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

# Create database tables and initial admin user
with app.app_context():
    db.create_all()
    
    # Add missing columns if they don't exist (migration)
    try:
        from sqlalchemy import text, inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'teacher_id' not in columns:
            # Column doesn't exist, add it
            db.session.execute(text("ALTER TABLE users ADD COLUMN teacher_id INTEGER REFERENCES teachers(id)"))
            db.session.commit()
            print("✅ Added teacher_id column to users table")
        
        if 'status' not in columns:
            # Column doesn't exist, add it
            db.session.execute(text("ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'approved'"))
            db.session.commit()
            # Update existing users to approved status
            db.session.execute(text("UPDATE users SET status = 'approved' WHERE status IS NULL"))
            db.session.commit()
            print("✅ Added status column to users table")
        
        # Make password_hash nullable if it's not already
        try:
            columns = [col['name'] for col in inspector.get_columns('users')]
            if 'password_hash' in columns:
                # Check if column is nullable
                password_hash_col = next((col for col in inspector.get_columns('users') if col['name'] == 'password_hash'), None)
                if password_hash_col and not password_hash_col.get('nullable', False):
                    db.session.execute(text("ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL"))
                    db.session.commit()
                    print("✅ Made password_hash nullable in users table")
        except Exception as e:
            print(f"⚠️ Password hash migration check failed: {e}")
            db.session.rollback()
        
        # Make email nullable if it's not already
        try:
            columns = [col['name'] for col in inspector.get_columns('users')]
            if 'email' in columns:
                # Check if column is nullable
                email_col = next((col for col in inspector.get_columns('users') if col['name'] == 'email'), None)
                if email_col and not email_col.get('nullable', False):
                    db.session.execute(text("ALTER TABLE users ALTER COLUMN email DROP NOT NULL"))
                    db.session.commit()
                    print("✅ Made email nullable in users table")
        except Exception as e:
            print(f"⚠️ Email migration check failed: {e}")
            db.session.rollback()
        
        # Check if teacher_update_requests table exists
        try:
            tables = [t for t in inspector.get_table_names()]
            if 'teacher_update_requests' not in tables:
                db.session.execute(text("""
                    CREATE TABLE teacher_update_requests (
                        id SERIAL PRIMARY KEY,
                        teacher_id INTEGER NOT NULL REFERENCES teachers(id),
                        requested_subject_ids TEXT NOT NULL,
                        requested_class_ids TEXT NOT NULL,
                        status VARCHAR(20) DEFAULT 'pending' NOT NULL,
                        admin_notes TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
                    )
                """))
                db.session.commit()
                print("✅ Created teacher_update_requests table")
        except Exception as e:
            print(f"⚠️ Teacher update requests table check failed: {e}")
            db.session.rollback()
        
        # Check if classes table has grade column
        try:
            columns = [col['name'] for col in inspector.get_columns('classes')]
            if 'grade' not in columns:
                db.session.execute(text("ALTER TABLE classes ADD COLUMN grade INTEGER"))
                db.session.commit()
                print("✅ Added grade column to classes table")
        except Exception as e:
            print(f"⚠️ Grade column migration check failed: {e}")
            db.session.rollback()
        
        # Check if teacher_subjects table exists
        try:
            tables = [t for t in inspector.get_table_names()]
            if 'teacher_subjects' not in tables:
                # Create teacher_subjects association table
                db.session.execute(text("""
                    CREATE TABLE teacher_subjects (
                        teacher_id INTEGER NOT NULL,
                        subject_id INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (teacher_id, subject_id),
                        FOREIGN KEY (teacher_id) REFERENCES teachers(id),
                        FOREIGN KEY (subject_id) REFERENCES subjects(id)
                    )
                """))
                db.session.commit()
                print("✅ Created teacher_subjects association table")
        except Exception as e:
            print(f"⚠️ Teacher subjects table check failed: {e}")
            db.session.rollback()
    except Exception as e:
        print(f"⚠️ Migration check failed: {e}")
        db.session.rollback()
    
    # Create initial admin user if it doesn't exist
    admin_user = User.query.filter_by(username='ravi').first()
    if not admin_user:
        admin_user = User(
            username='ravi',
            email='ravi@school.com',
            is_admin=True,
            status='approved'  # Admin is auto-approved
        )
        admin_user.set_password('School@143')
        db.session.add(admin_user)
        db.session.commit()
        print("✅ Initial admin user 'ravi' created successfully!")


# Authentication decorator
def login_required(f):
    """Decorator to require login for protected routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # If it's an API request (JSON), return JSON error
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            # Otherwise redirect to login page
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication."""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Username and password are required'}), 400
            return render_template('login.html', error='Username and password are required')
        
        user = User.query.filter_by(username=username).first()
        
        if not user:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
            return render_template('login.html', error='Invalid username or password')
        
        # Check if user needs to set password (admin-created account)
        if not user.password_hash:
            if request.is_json:
                return jsonify({
                    'success': False, 
                    'message': 'Please set your password first. Use the signup page to set your password.',
                    'needs_password_setup': True
                }), 401
            return render_template('login.html', error='Please set your password first. Use the signup page to set your password.')
        
        if not user.check_password(password):
            if request.is_json:
                return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
            return render_template('login.html', error='Invalid username or password')
        
        # Check if user is approved
        if user.status != 'approved':
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Your account is pending approval. Please wait for admin approval.'
                }), 403
            return render_template('login.html', error='Your account is pending approval. Please wait for admin approval.')
        
        session['user_id'] = user.id
        session['username'] = user.username
        session['is_admin'] = user.is_admin
        
        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': user.to_dict()
            })
        # Redirect based on user type
        if user.is_admin:
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('dashboard'))
    
    # GET request - show login page
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page for new users."""
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        
        # Validation
        if not username or not password:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Username and password are required'}), 400
            return render_template('signup.html', error='Username and password are required')
        
        # Trim whitespace from username
        username = username.strip()
        
        # Email is optional
        email = email.strip() if email else None
        
        if password != confirm_password:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Passwords do not match'}), 400
            return render_template('signup.html', error='Passwords do not match')
        
        # Check if username already exists (case-insensitive)
        from sqlalchemy import func
        existing_user = User.query.filter(func.lower(User.username) == username.lower()).first()
        
        # Also check if there's a user with this username that has a teacher_id (admin-created)
        # This handles cases where the username might have slight differences
        if not existing_user:
            # Try to find by teacher name if username doesn't match
            # This is a fallback in case username was stored differently
            teacher_user = User.query.filter(
                User.teacher_id.isnot(None),
                func.lower(User.username).like(f'%{username.lower()}%')
            ).first()
            if teacher_user:
                existing_user = teacher_user
        
        if existing_user:
            # If user exists but has no password (admin-created account), allow setting password
            # Check explicitly for None or empty string
            # Admin-created accounts have teacher_id and no password_hash
            has_no_password = existing_user.password_hash is None or existing_user.password_hash == '' or str(existing_user.password_hash).strip() == ''
            is_admin_created = existing_user.teacher_id is not None
            
            # Allow password setup if: no password exists OR it's an admin-created account (even if password_hash has unexpected value)
            # Admin-created accounts should always be able to set their password
            if has_no_password or (is_admin_created and existing_user.status == 'approved'):
                # User exists without password - set password
                existing_user.set_password(password)
                # Ensure status remains 'approved' (admin-created accounts are already approved)
                if existing_user.status != 'approved':
                    existing_user.status = 'approved'
                # Email might be updated (if provided and different)
                if email and existing_user.email != email:
                    # Check if new email is already taken
                    email_taken = User.query.filter_by(email=email).first()
                    if email_taken and email_taken.id != existing_user.id:
                        if request.is_json:
                            return jsonify({'success': False, 'message': 'Email already exists'}), 400
                        return render_template('signup.html', error='Email already exists')
                    existing_user.email = email
                elif not existing_user.email and email:
                    # User has no email, set it if provided
                    existing_user.email = email
                
                try:
                    db.session.commit()
                    if request.is_json:
                        return jsonify({
                            'success': True,
                            'message': 'Password set successfully! You can now login immediately.'
                        })
                    return render_template('signup.html', success='Password set successfully! You can now login immediately.')
                except Exception as e:
                    db.session.rollback()
                    if request.is_json:
                        return jsonify({'success': False, 'message': f'Error setting password: {str(e)}'}), 500
                    return render_template('signup.html', error=f'Error setting password: {str(e)}')
            else:
                # User exists with password
                if request.is_json:
                    return jsonify({'success': False, 'message': 'Username already exists. If this is your account, please login instead.'}), 400
                return render_template('signup.html', error='Username already exists. If this is your account, please login instead.')
        
        # Before creating new user, double-check no case-insensitive duplicate exists
        # (This handles edge cases where the query might have missed something)
        duplicate_check = User.query.filter(func.lower(User.username) == username.lower()).first()
        if duplicate_check:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Username already exists. If this is your account, please login instead.'}), 400
            return render_template('signup.html', error='Username already exists. If this is your account, please login instead.')
        
        # Create new user with pending status
        new_user = User(
            username=username,
            email=email,
            is_admin=False,
            status='pending'
        )
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Signup successful! Your account is pending admin approval.'
                })
            return render_template('signup.html', success='Signup successful! Your account is pending admin approval. You will be able to login once approved.')
        except Exception as e:
            db.session.rollback()
            if request.is_json:
                return jsonify({'success': False, 'message': f'Error creating account: {str(e)}'}), 500
            return render_template('signup.html', error=f'Error creating account: {str(e)}')
    
    # GET request - show signup page
    return render_template('signup.html')


@app.route('/logout')
def logout():
    """Logout and clear session."""
    session.clear()
    return redirect(url_for('login'))


@app.route('/api/auth/check')
def check_auth():
    """Check if user is authenticated (API endpoint)."""
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            return jsonify({
                'success': True,
                'authenticated': True,
                'user': user.to_dict(),
                'current_user_id': user.id
            })
    return jsonify({
        'success': True,
        'authenticated': False
    })


@app.route('/api/pending-users', methods=['GET'])
@login_required
def get_pending_users():
    """Get all pending user requests (admin only)."""
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    pending_users = User.query.filter_by(status='pending').all()
    return jsonify({
        'success': True,
        'users': [u.to_dict() for u in pending_users]
    })


@app.route('/api/users/<int:user_id>/approve', methods=['POST'])
@login_required
def approve_user(user_id):
    """
    Approve a pending user (admin only).
    Optionally create teacher profile and link it to the user.
    
    Request body (optional):
        create_teacher: boolean - whether to create teacher profile
        teacher_name: string - name for teacher profile
        is_class_teacher: boolean - if teacher is a class teacher
        subject_ids: array - list of subject IDs the teacher teaches
        class_id: integer - ID of the class if teacher is a class teacher
    """
    admin_user = User.query.get(session['user_id'])
    if not admin_user or not admin_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    user = User.query.get_or_404(user_id)
    if user.status != 'pending':
        return jsonify({
            'success': False,
            'message': f'User is already {user.status}'
        }), 400
    
    data = request.get_json() or {}
    create_teacher = data.get('create_teacher', False)
    
    user.status = 'approved'
    
    # Optionally create teacher profile
    if create_teacher:
        teacher_name = data.get('teacher_name', user.username)
        is_class_teacher = data.get('is_class_teacher', False)
        class_id = data.get('class_id')
        subject_ids = data.get('subject_ids', [])
        
        # Validate class_id if class teacher
        class_obj = None
        if is_class_teacher and class_id:
            class_obj = Class.query.get(class_id)
            if not class_obj:
                return jsonify({
                    'success': False,
                    'message': f'Class with ID {class_id} not found'
                }), 400
            # Check if class already has a class teacher
            if class_obj.class_teacher_id:
                existing_teacher = Teacher.query.get(class_obj.class_teacher_id)
                return jsonify({
                    'success': False,
                    'message': f'Class {class_obj.name} already has a class teacher: {existing_teacher.name if existing_teacher else "Unknown"}'
                }), 400
        
        # Create teacher profile
        teacher = Teacher(
            name=teacher_name,
            is_class_teacher=is_class_teacher,
            is_leisure=False  # Default to False, can be updated later if needed
        )
        db.session.add(teacher)
        db.session.flush()  # Get teacher ID
        
        # Link user to teacher
        user.teacher_id = teacher.id
        
        # Link teacher to class if class teacher
        if is_class_teacher and class_obj:
            class_obj.class_teacher_id = teacher.id
        
        # Add subjects if provided
        if subject_ids:
            subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all()
            teacher.subjects = subjects
    
    db.session.commit()
    
    response_data = {
        'success': True,
        'message': f'User {user.username} has been approved',
        'user': user.to_dict()
    }
    
    if create_teacher:
        response_data['teacher_id'] = teacher.id
        if is_class_teacher and class_obj:
            response_data['class_id'] = class_obj.id
            response_data['message'] += f' and assigned as class teacher for {class_obj.name}'
        else:
            response_data['message'] += ' and teacher profile created'
    
    return jsonify(response_data)


@app.route('/api/users/<int:user_id>/reject', methods=['POST'])
@login_required
def reject_user(user_id):
    """Reject a pending user (admin only)."""
    admin_user = User.query.get(session['user_id'])
    if not admin_user or not admin_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    user = User.query.get_or_404(user_id)
    if user.status != 'pending':
        return jsonify({
            'success': False,
            'message': f'User is already {user.status}'
        }), 400
    
    user.status = 'rejected'
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'User {user.username} has been rejected',
        'user': user.to_dict()
    })


@app.route('/api/users', methods=['GET'])
@login_required
def get_all_users():
    """Get all users (admin only)."""
    admin_user = User.query.get(session['user_id'])
    if not admin_user or not admin_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify({
        'success': True,
        'users': [u.to_dict() for u in users]
    })


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """Delete a user (admin only)."""
    admin_user = User.query.get(session['user_id'])
    if not admin_user or not admin_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    user = User.query.get_or_404(user_id)
    
    # Prevent admin from deleting themselves
    if user.id == admin_user.id:
        return jsonify({
            'success': False,
            'message': 'You cannot delete your own account'
        }), 400
    
    username = user.username
    
    try:
        # Delete associated teacher if exists
        if user.teacher_id:
            teacher = Teacher.query.get(user.teacher_id)
            if teacher:
                # Check if this teacher is used as class teacher
                classes_using_teacher = Class.query.filter_by(class_teacher_id=teacher.id).all()
                for class_obj in classes_using_teacher:
                    class_obj.class_teacher_id = None
                
                # Delete teacher's schedules
                Schedule.query.filter_by(teacher_id=teacher.id).delete()
                
                # Delete teacher's absences (as absent teacher)
                Absence.query.filter_by(teacher_id=teacher.id).delete()
                
                # Delete teacher's substitutions (as substitute teacher)
                Absence.query.filter_by(substitute_teacher_id=teacher.id).delete()
                
                # Clear teacher-subjects associations (many-to-many)
                # Clear the relationship using ORM
                teacher.subjects = []
                db.session.flush()  # Ensure the association is cleared before deleting
                
                db.session.delete(teacher)
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'User {username} has been deleted successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting user: {str(e)}. The user may be referenced by schedules, absences, or other data.'
        }), 500


@app.route('/')
def index():
    """
    Main page route - redirects to login or dashboard based on auth status.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # If logged in, redirect based on user type
    user = User.query.get(session['user_id'])
    if user and user.is_admin:
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('dashboard'))


@app.route('/admin')
@login_required
def admin():
    """
    Admin setup page - for initial school configuration.
    Requires authentication and admin privileges.
    """
    user = User.query.get(session['user_id'])
    if not user or not user.is_admin:
        return redirect(url_for('dashboard'))
    return render_template('admin.html')


@app.route('/dashboard')
@login_required
def dashboard():
    """
    User dashboard - shows personal timetable for logged-in user.
    """
    user = User.query.get(session['user_id'])
    if not user:
        return redirect(url_for('login'))
    
    # If admin, redirect to admin panel
    if user.is_admin:
        return redirect(url_for('admin'))
    
    # Get teacher associated with this user
    teacher = None
    if user.teacher_id:
        teacher = Teacher.query.get(user.teacher_id)
    
    return render_template('dashboard.html', user=user, teacher=teacher, date=date)


@app.route('/api/generate-schedule', methods=['POST'])
@login_required
def generate_schedule():
    """
    Generate schedule following custom rules:
    - Sundays are holidays (no schedules)
    - 6th and 7th: 6 subjects + library + games = 8 periods daily
    - 8th and 9th: 7 subjects + library/games (alternating) = 8 periods
    - 10th: Maths at 1st and last period, remaining 6 periods for other subjects (no library/games)
    - No overlaps: one teacher can't teach multiple classes at same period/day
    - Only assign teachers who actually teach that subject
    - Each subject has exactly one teacher per class
    """
    admin_user = User.query.get(session['user_id'])
    if not admin_user or not admin_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    try:
        # Clear existing schedules
        Schedule.query.delete()
        db.session.commit()
        
        # Get all data
        teachers = Teacher.query.filter_by(is_leisure=False).all()
        classes = Class.query.all()
        subjects = Subject.query.all()
        
        if not teachers or not classes or not subjects:
            return jsonify({
                'success': False,
                'message': 'Please add teachers, classes, and subjects first.'
            }), 400
        
        # Check if classes have grades set
        classes_without_grade = [c.name for c in classes if c.grade is None]
        if classes_without_grade:
            return jsonify({
                'success': False,
                'message': f'Please set grade for classes: {", ".join(classes_without_grade)}'
            }), 400
        
        # Find special subjects (Library, Games, Maths, Physical Science, Bio Science)
        library_subject = Subject.query.filter(func.lower(Subject.name) == 'library').first()
        games_subject = Subject.query.filter(func.lower(Subject.name) == 'games').first()
        maths_subject = Subject.query.filter(func.lower(Subject.name) == 'maths').first()
        if not maths_subject:
            maths_subject = Subject.query.filter(func.lower(Subject.name) == 'mathematics').first()
        
        # For 6th/7th grade: Physical Science and Bio Science become "Science"
        physical_science_subject = Subject.query.filter(
            func.lower(Subject.name).in_(['physical science', 'physics'])
        ).first()
        bio_science_subject = Subject.query.filter(
            func.lower(Subject.name).in_(['bio science', 'biology', 'biological science'])
        ).first()
        science_subject = Subject.query.filter(func.lower(Subject.name) == 'science').first()
        
        # Build teacher-subject map (which teachers teach which subjects)
        teacher_subject_map = {}  # {teacher_id: set(subject_ids)}
        for teacher in teachers:
            teacher_subject_map[teacher.id] = {s.id for s in teacher.subjects}
        
        # Build subject-teacher map (which teachers can teach each subject)
        subject_teacher_map = {}  # {subject_id: [teacher_ids]}
        for subject in subjects:
            subject_teacher_map[subject.id] = [
                t.id for t in teachers if subject.id in teacher_subject_map.get(t.id, set())
            ]
        
        # For 6th/7th grade: Create special "Science" subject mapping
        # Science should be taught by Bio Science teachers
        if bio_science_subject:
            bio_science_teachers = subject_teacher_map.get(bio_science_subject.id, [])
            # If we have a "Science" subject, add bio science teachers to it
            if science_subject:
                subject_teacher_map[science_subject.id] = list(set(
                    subject_teacher_map.get(science_subject.id, []) + bio_science_teachers
                ))
            # Also allow using bio_science_subject directly as "Science" for 6th/7th
            if bio_science_subject.id not in subject_teacher_map:
                subject_teacher_map[bio_science_subject.id] = bio_science_teachers
        
        # Helper: Get available teacher for a subject at a specific period/day
        def get_available_teacher_for_subject(subject_id, day, period, exclude_class_id=None, allow_no_teacher=False):
            """Find a teacher who can teach this subject and is free at this period.
            If allow_no_teacher is True, returns a special marker (-1) if no teacher is available.
            """
            # Library and Games don't require teachers
            if allow_no_teacher:
                # Return a placeholder teacher ID (-1) to indicate no teacher needed
                # We'll handle this specially when creating the schedule
                return -1
            
            # Get teachers who can teach this subject
            candidate_teachers = subject_teacher_map.get(subject_id, [])
            
            if not candidate_teachers:
                return None
            
            # Check which teachers are already assigned at this period/day
            busy_teachers = set()
            existing_schedules = Schedule.query.filter_by(day=day, period=period).all()
            for sched in existing_schedules:
                if sched.class_id != exclude_class_id:  # Allow same teacher for same class
                    busy_teachers.add(sched.teacher_id)
            
            # Find available teacher
            for teacher_id in candidate_teachers:
                if teacher_id not in busy_teachers:
                    return teacher_id
            
            return None
        
        # Track unscheduled periods and missing requirements
        unscheduled_periods = []
        missing_requirements = {
            'subjects_without_teachers': {},  # {subject_name: [class_names]}
            'classes_missing_subjects': {},  # {class_name: [subject_names]}
            'classes_missing_teachers': {},  # {class_name: {subject: [periods]}}
            'summary': []
        }
        
        # Pre-check: Identify subjects that have no teachers assigned
        subjects_without_any_teacher = []
        for subject in subjects:
            if subject.id not in subject_teacher_map or len(subject_teacher_map[subject.id]) == 0:
                subjects_without_any_teacher.append(subject.name)
        
        if subjects_without_any_teacher:
            missing_requirements['summary'].append(
                f"Subjects with no teachers assigned: {', '.join(subjects_without_any_teacher)}"
            )
        
        # Track subject-teacher assignments per class (to ensure consistency across days)
        # {class_id: {subject_id: teacher_id}}
        class_subject_teacher_map = {}
        
        # Generate schedule for Monday-Friday (0-4), Sunday (6) is holiday
        for day in range(5):  # Monday to Friday
            for class_obj in classes:
                # Initialize class-subject-teacher map if not exists
                if class_obj.id not in class_subject_teacher_map:
                    class_subject_teacher_map[class_obj.id] = {}
                grade = class_obj.grade
                
                if grade in [6, 7]:
                    # 6th and 7th: 6 unique subjects + library + games = 8 periods (no subject repeats)
                    # Physical Science and Bio Science become "Science" (taught by Bio Science teachers)
                    # Get regular subjects (exclude library, games, physical science)
                    regular_subjects = [
                        s for s in subjects 
                        if s.id != (library_subject.id if library_subject else None)
                        and s.id != (games_subject.id if games_subject else None)
                        and s.id != (physical_science_subject.id if physical_science_subject else None)
                    ]
                    
                    # Replace Bio Science with "Science" if Science subject exists, otherwise use Bio Science
                    science_subject_to_use = None
                    if science_subject:
                        science_subject_to_use = science_subject
                    elif bio_science_subject:
                        science_subject_to_use = bio_science_subject
                    
                    # Remove bio science from regular subjects if we're using it as Science
                    if bio_science_subject and science_subject_to_use:
                        regular_subjects = [s for s in regular_subjects if s.id != bio_science_subject.id]
                    
                    # Take up to 5 regular subjects (we'll add Science as the 6th)
                    regular_subjects = regular_subjects[:5]
                    
                    # Add Science as one of the 6 subjects (if available)
                    if science_subject_to_use:
                        regular_subjects.append(science_subject_to_use)
                    
                    # Ensure we have exactly 6 unique subjects
                    regular_subjects = regular_subjects[:6]
                    
                    # Check what subjects are already scheduled for this class on this day to avoid duplicates
                    existing_subjects_today = set()
                    existing_schedules_today = Schedule.query.filter_by(
                        class_id=class_obj.id,
                        day=day
                    ).all()
                    for sched in existing_schedules_today:
                        existing_subjects_today.add(sched.subject_id)
                    
                    # Period 1: Class teacher if available
                    period1_assigned = False
                    if class_obj.class_teacher_id and day == 0:  # Only on first day (Monday) for class teacher
                        class_teacher = Teacher.query.get(class_obj.class_teacher_id)
                        if class_teacher and regular_subjects:
                            # Use first subject that hasn't been scheduled yet today
                            subject_for_period1 = None
                            for subj in regular_subjects:
                                if subj.id not in existing_subjects_today:
                                    subject_for_period1 = subj
                                    break
                            if not subject_for_period1:
                                subject_for_period1 = regular_subjects[0]  # Fallback to first subject
                            
                            schedule = Schedule(
                                teacher_id=class_teacher.id,
                                class_id=class_obj.id,
                                subject_id=subject_for_period1.id,
                                day=day,
                                period=1
                            )
                            db.session.add(schedule)
                            existing_subjects_today.add(subject_for_period1.id)
                            # Store this assignment for consistency across days
                            class_subject_teacher_map[class_obj.id][subject_for_period1.id] = class_teacher.id
                            period1_assigned = True
                    
                    # Period 1-6: Regular subjects (each subject appears only once per day)
                    for period in range(1, 7):
                        # Skip period 1 if class teacher already assigned it
                        if period == 1 and period1_assigned:
                            continue
                        
                        # Find a subject that hasn't been scheduled yet today
                        subject = None
                        for subj in regular_subjects:
                            if subj.id not in existing_subjects_today:
                                subject = subj
                                break
                        
                        if not subject:
                            # All subjects scheduled, skip
                            break
                        
                        teacher_id = get_available_teacher_for_subject(subject.id, day, period, class_obj.id)
                        
                        # If no teacher available, use placeholder teacher
                        if not teacher_id:
                            placeholder_teacher = teachers[0] if teachers else None
                            if placeholder_teacher:
                                teacher_id = placeholder_teacher.id
                            else:
                                unscheduled_periods.append(f"{class_obj.name} Day {day+1} Period {period}: {subject.name} (no teachers in system)")
                                continue
                        
                        schedule = Schedule(
                            teacher_id=teacher_id,
                            class_id=class_obj.id,
                            subject_id=subject.id,
                            day=day,
                            period=period
                        )
                        db.session.add(schedule)
                        existing_subjects_today.add(subject.id)
                    
                    # Period 7: Library (no teacher required)
                    if library_subject:
                        # Library doesn't need a teacher - use placeholder teacher
                        teacher_id = get_available_teacher_for_subject(library_subject.id, day, 7, class_obj.id, allow_no_teacher=True)
                        if teacher_id == -1 or teacher_id is None:
                            # Use first teacher as placeholder (they won't actually teach Library)
                            placeholder_teacher = teachers[0] if teachers else None
                            if placeholder_teacher:
                                teacher_id = placeholder_teacher.id
                            else:
                                continue  # Skip if no teachers exist
                        
                        schedule = Schedule(
                            teacher_id=teacher_id,
                            class_id=class_obj.id,
                            subject_id=library_subject.id,
                            day=day,
                            period=7
                        )
                        db.session.add(schedule)
                    else:
                        unscheduled_periods.append(f"{class_obj.name} Day {day+1} Period 7: Library subject not found")
                        missing_requirements['summary'].append(f"{class_obj.name}: Library subject not found in database")
                    
                    # Period 8: Games (no teacher required)
                    if games_subject:
                        # Games doesn't need a teacher - use placeholder teacher
                        teacher_id = get_available_teacher_for_subject(games_subject.id, day, 8, class_obj.id, allow_no_teacher=True)
                        if teacher_id == -1 or teacher_id is None:
                            # Use first teacher as placeholder
                            placeholder_teacher = teachers[0] if teachers else None
                            if placeholder_teacher:
                                teacher_id = placeholder_teacher.id
                            else:
                                continue
                        
                        schedule = Schedule(
                            teacher_id=teacher_id,
                            class_id=class_obj.id,
                            subject_id=games_subject.id,
                            day=day,
                            period=8
                        )
                        db.session.add(schedule)
                    else:
                        unscheduled_periods.append(f"{class_obj.name} Day {day+1} Period 8: Games subject not found")
                        missing_requirements['summary'].append(f"{class_obj.name}: Games subject not found in database")
                
                elif grade in [8, 9]:
                    # 8th and 9th: 7 unique subjects + library/games (alternating) = 8 periods (no subject repeats)
                    # Get 7 regular subjects (exclude library, games)
                    regular_subjects = [
                        s for s in subjects 
                        if s.id != (library_subject.id if library_subject else None)
                        and s.id != (games_subject.id if games_subject else None)
                    ][:7]
                    
                    # Check what subjects are already scheduled for this class on this day to avoid duplicates
                    existing_subjects_today = set()
                    existing_schedules_today = Schedule.query.filter_by(
                        class_id=class_obj.id,
                        day=day
                        ).all()
                    for sched in existing_schedules_today:
                        existing_subjects_today.add(sched.subject_id)
                    
                    # Period 1: Class teacher if available
                    period1_assigned = False
                    if class_obj.class_teacher_id and day == 0:  # Only on first day (Monday) for class teacher
                        class_teacher = Teacher.query.get(class_obj.class_teacher_id)
                        if class_teacher and regular_subjects:
                            # Use first subject that hasn't been scheduled yet today
                            subject_for_period1 = None
                            for subj in regular_subjects:
                                if subj.id not in existing_subjects_today:
                                    subject_for_period1 = subj
                                    break
                            if not subject_for_period1:
                                subject_for_period1 = regular_subjects[0]  # Fallback to first subject
                            
                            schedule = Schedule(
                                teacher_id=class_teacher.id,
                                class_id=class_obj.id,
                                subject_id=subject_for_period1.id,
                                day=day,
                                period=1
                            )
                            db.session.add(schedule)
                            existing_subjects_today.add(subject_for_period1.id)
                            # Store this assignment for consistency across days
                            class_subject_teacher_map[class_obj.id][subject_for_period1.id] = class_teacher.id
                            period1_assigned = True
                    
                    # Period 1-7: Regular subjects (each subject appears only once per day)
                    for period in range(1, 8):
                        # Skip period 1 if class teacher already assigned it
                        if period == 1 and period1_assigned:
                            continue
                        
                        # Find a subject that hasn't been scheduled yet today
                        subject = None
                        for subj in regular_subjects:
                            if subj.id not in existing_subjects_today:
                                subject = subj
                                break
                        
                        if not subject:
                            # All subjects scheduled, skip
                            break
                        
                        # Check if this subject already has a teacher assigned for this class (from previous days)
                        if subject.id in class_subject_teacher_map[class_obj.id]:
                            teacher_id = class_subject_teacher_map[class_obj.id][subject.id]
                        else:
                            # First time assigning this subject to this class - find a teacher
                            teacher_id = get_available_teacher_for_subject(subject.id, day, period, class_obj.id)
                            
                            # If no teacher available, use placeholder teacher
                            if not teacher_id:
                                placeholder_teacher = teachers[0] if teachers else None
                                if placeholder_teacher:
                                    teacher_id = placeholder_teacher.id
                                else:
                                    unscheduled_periods.append(f"{class_obj.name} Day {day+1} Period {period}: {subject.name} (no teachers in system)")
                                    continue
                            
                            # Store this assignment for future days
                            class_subject_teacher_map[class_obj.id][subject.id] = teacher_id
                        
                        schedule = Schedule(
                            teacher_id=teacher_id,
                            class_id=class_obj.id,
                            subject_id=subject.id,
                            day=day,
                            period=period
                        )
                        db.session.add(schedule)
                        existing_subjects_today.add(subject.id)
                    
                    # Period 8: Library or Games (alternating days) - no teacher required
                    # Monday, Wednesday, Friday = Library; Tuesday, Thursday = Games
                    period8_subject = library_subject if day in [0, 2, 4] else games_subject
                    if period8_subject:
                        # Library/Games don't require teachers
                        teacher_id = get_available_teacher_for_subject(period8_subject.id, day, 8, class_obj.id, allow_no_teacher=True)
                        if teacher_id is None:
                            continue
                        if teacher_id == -1:
                            # Use placeholder teacher
                            placeholder_teacher = teachers[0] if teachers else None
                            if placeholder_teacher:
                                teacher_id = placeholder_teacher.id
                            else:
                                continue
                        
                        schedule = Schedule(
                            teacher_id=teacher_id,
                            class_id=class_obj.id,
                            subject_id=period8_subject.id,
                            day=day,
                            period=8
                        )
                        db.session.add(schedule)
                    else:
                        unscheduled_periods.append(f"{class_obj.name} Day {day+1} Period 8: Library/Games subject not found")
                        missing_requirements['summary'].append(f"{class_obj.name}: Library/Games subject not found in database")
                
                elif grade == 10:
                    # 10th: Maths at 1st and last period, remaining 6 periods for other unique subjects
                    # Maths is the only subject that can repeat (periods 1 and 8)
                    if not maths_subject:
                        unscheduled_periods.append(f"{class_obj.name} Day {day+1}: Maths subject not found")
                        missing_requirements['summary'].append(f"{class_obj.name}: Maths subject not found in database")
                        continue  # Skip if no Maths subject
                    
                    # Check what subjects are already scheduled for this class on this day (excluding Maths which can repeat)
                    existing_subjects_today = set()
                    existing_schedules_today = Schedule.query.filter_by(
                        class_id=class_obj.id,
                        day=day
                    ).all()
                    for sched in existing_schedules_today:
                        # Don't count Maths as existing since it can appear twice
                        if sched.subject_id != maths_subject.id:
                            existing_subjects_today.add(sched.subject_id)
                    
                    # Period 1: Maths (class teacher if available, otherwise any teacher or placeholder)
                    if class_obj.class_teacher_id and day == 0:  # Class teacher on Monday
                        class_teacher = Teacher.query.get(class_obj.class_teacher_id)
                        if class_teacher:
                            teacher_id = class_teacher.id
                        else:
                            teacher_id = get_available_teacher_for_subject(maths_subject.id, day, 1, class_obj.id)
                            if not teacher_id:
                                teacher_id = teachers[0].id if teachers else None
                    else:
                        teacher_id = get_available_teacher_for_subject(maths_subject.id, day, 1, class_obj.id)
                        if not teacher_id:
                            teacher_id = teachers[0].id if teachers else None
                    
                    if teacher_id:
                        schedule = Schedule(
                            teacher_id=teacher_id,
                            class_id=class_obj.id,
                            subject_id=maths_subject.id,
                            day=day,
                            period=1
                        )
                        db.session.add(schedule)
                    
                    # Period 2-7: Other subjects (exclude Maths) - each subject appears only once
                    other_subjects = [
                        s for s in subjects 
                        if s.id != maths_subject.id
                    ][:6]
                    
                    for period in range(2, 8):
                        # Find a subject that hasn't been scheduled yet today
                        subject = None
                        for subj in other_subjects:
                            if subj.id not in existing_subjects_today:
                                subject = subj
                                break
                        
                        if not subject:
                            # All subjects scheduled, skip
                            break
                        
                        # Check if this subject already has a teacher assigned for this class (from previous days)
                        if subject.id in class_subject_teacher_map[class_obj.id]:
                            teacher_id = class_subject_teacher_map[class_obj.id][subject.id]
                        else:
                            # First time assigning this subject to this class - find a teacher
                            teacher_id = get_available_teacher_for_subject(subject.id, day, period, class_obj.id)
                            
                            # If no teacher available, use placeholder teacher
                            if not teacher_id:
                                placeholder_teacher = teachers[0] if teachers else None
                                if placeholder_teacher:
                                    teacher_id = placeholder_teacher.id
                                else:
                                    unscheduled_periods.append(f"{class_obj.name} Day {day+1} Period {period}: {subject.name} (no teachers in system)")
                                    continue
                            
                            # Store this assignment for future days
                            class_subject_teacher_map[class_obj.id][subject.id] = teacher_id
                        
                        schedule = Schedule(
                            teacher_id=teacher_id,
                            class_id=class_obj.id,
                            subject_id=subject.id,
                            day=day,
                            period=period
                        )
                        db.session.add(schedule)
                        existing_subjects_today.add(subject.id)
                    
                    # Period 8: Maths (use the same teacher as period 1 for consistency)
                    if maths_subject.id in class_subject_teacher_map[class_obj.id]:
                        teacher_id = class_subject_teacher_map[class_obj.id][maths_subject.id]
                    else:
                        # Fallback (shouldn't happen if period 1 was assigned)
                        teacher_id = get_available_teacher_for_subject(maths_subject.id, day, 8, class_obj.id)
                        if not teacher_id:
                            teacher_id = teachers[0].id if teachers else None
                        class_subject_teacher_map[class_obj.id][maths_subject.id] = teacher_id
                    
                    if teacher_id:
                        schedule = Schedule(
                            teacher_id=teacher_id,
                            class_id=class_obj.id,
                            subject_id=maths_subject.id,
                            day=day,
                            period=8
                        )
                        db.session.add(schedule)
        
        db.session.commit()
        
        # Build detailed missing requirements report
        detailed_report = []
        
        # Summary of subjects without any teachers
        if missing_requirements['summary']:
            detailed_report.extend(missing_requirements['summary'])
        
        # Subjects that need teachers for specific classes (exclude Library and Games)
        if missing_requirements['subjects_without_teachers']:
            detailed_report.append("\n📚 Subjects needing teachers:")
            for subject_name, class_list in missing_requirements['subjects_without_teachers'].items():
                # Skip Library and Games - they don't need teachers
                if subject_name.lower() in ['library', 'games']:
                    continue
                unique_classes = list(set(class_list))
                detailed_report.append(f"  • {subject_name}: Needs teacher(s) for classes: {', '.join(unique_classes)}")
        
        # Classes missing teachers for specific subjects (exclude Library and Games)
        if missing_requirements['classes_missing_teachers']:
            detailed_report.append("\n👨‍🏫 Classes missing teachers for subjects:")
            for class_name, subjects_dict in missing_requirements['classes_missing_teachers'].items():
                # Filter out Library and Games
                filtered_subjects = {k: v for k, v in subjects_dict.items() if k.lower() not in ['library', 'games']}
                if not filtered_subjects:
                    continue
                detailed_report.append(f"  • {class_name}:")
                for subject_name, periods in filtered_subjects.items():
                    unique_periods = list(set(periods))
                    period_count = len(unique_periods)
                    if period_count <= 3:
                        detailed_report.append(f"    - {subject_name}: Needs teacher for {', '.join(unique_periods)}")
                    else:
                        detailed_report.append(f"    - {subject_name}: Needs teacher for {period_count} periods (e.g., {', '.join(unique_periods[:3])}...)")
        
        # Classes missing subjects
        if missing_requirements['classes_missing_subjects']:
            detailed_report.append("\n📖 Classes missing subjects:")
            for class_name, periods in missing_requirements['classes_missing_subjects'].items():
                unique_periods = list(set(periods))
                detailed_report.append(f"  • {class_name}: Missing subjects for periods: {', '.join(unique_periods)}")
        
        # Build response message
        if unscheduled_periods:
            message = f'Schedule generated with {len(unscheduled_periods)} unscheduled periods. See details below.'
        else:
            message = f'Schedule generated successfully for {len(classes)} classes following grade-specific rules.'
        
        response_data = {
            'success': True,
            'message': message,
            'unscheduled_count': len(unscheduled_periods),
            'missing_requirements': missing_requirements,
            'detailed_report': '\n'.join(detailed_report) if detailed_report else 'All requirements met!'
        }
        
        return jsonify(response_data)
    
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error generating schedule: {str(e)}'
        }), 500


@app.route('/api/absent-teachers', methods=['GET', 'POST'])
def absent_teachers():
    """
    Handle absent teachers - GET shows absences, POST marks a teacher as absent.
    GET is public, POST requires authentication.
    
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
    if request.method == 'POST':
        # POST requires authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
    if request.method == 'GET':
        teachers_list = Teacher.query.all()
        return jsonify({
            'success': True,
            'teachers': [t.to_dict() for t in teachers_list]
        })
    elif request.method == 'POST':
        data = request.get_json()
        is_class_teacher = data.get('is_class_teacher', False)
        class_id = data.get('class_id')
        subject_ids = data.get('subject_ids', [])
        username = data.get('username')
        email = data.get('email')
        
        # Validate username is provided
        if not username:
            return jsonify({
                'success': False,
                'message': 'Username is required when creating a teacher'
            }), 400
        
        # Check if username already exists
        existing_user_by_username = User.query.filter_by(username=username).first()
        if existing_user_by_username:
            return jsonify({
                'success': False,
                'message': f'Username already exists: {username}'
            }), 400
        
        # Check if email already exists (only if email is provided)
        if email:
            existing_user_by_email = User.query.filter_by(email=email).first()
            if existing_user_by_email:
                return jsonify({
                    'success': False,
                    'message': f'Email already exists: {email}'
                }), 400
        
        # Validate class_id if class teacher
        class_obj = None
        if is_class_teacher and class_id:
            class_obj = Class.query.get(class_id)
            if not class_obj:
                return jsonify({
                    'success': False,
                    'message': f'Class with ID {class_id} not found'
                }), 400
            # Check if class already has a class teacher
            if class_obj.class_teacher_id:
                existing_teacher = Teacher.query.get(class_obj.class_teacher_id)
                return jsonify({
                    'success': False,
                    'message': f'Class {class_obj.name} already has a class teacher: {existing_teacher.name if existing_teacher else "Unknown"}'
                }), 400
        
        teacher = Teacher(
            name=data.get('name'),
            is_class_teacher=is_class_teacher,
            is_leisure=False  # Always False now
        )
        db.session.add(teacher)
        db.session.flush()  # Get teacher ID
        
        # Create user account for teacher (without password - user will set it via signup)
        new_user = User(
            username=username,
            email=email if email else None,  # Email is optional
            is_admin=False,
            status='approved',  # Admin-created accounts are auto-approved
            teacher_id=teacher.id,
            password_hash=None  # No password yet - user will set it
        )
        db.session.add(new_user)
        
        # Link teacher to class if class teacher
        if is_class_teacher and class_obj:
            class_obj.class_teacher_id = teacher.id
        
        # Add subjects if provided
        if subject_ids:
            subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all()
            teacher.subjects = subjects
        
        db.session.commit()
        
        response_data = {
            'success': True,
            'teacher': teacher.to_dict(),
            'message': f'Teacher created. User account "{username}" created. User can set password via signup page.'
        }
        if is_class_teacher and class_obj:
            response_data['class_id'] = class_obj.id
            response_data['message'] += f' Assigned as class teacher for {class_obj.name}.'
        
        return jsonify(response_data)


@app.route('/api/teachers/reset', methods=['POST'])
@login_required
def reset_teachers():
    """Reset teachers table (delete all and restart IDs) if nothing references them."""
    # Only admin can do this
    admin_user = User.query.get(session['user_id'])
    if not admin_user or not admin_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    # Check references: classes, schedules, absences, users, teacher_subjects
    has_class_refs = Class.query.filter(Class.class_teacher_id.isnot(None)).first() is not None
    has_schedule_refs = Schedule.query.filter(Schedule.teacher_id.isnot(None)).first() is not None
    has_absence_refs = Absence.query.filter(
        (Absence.teacher_id.isnot(None)) | (Absence.substitute_teacher_id.isnot(None))
    ).first() is not None
    has_user_refs = User.query.filter(User.teacher_id.isnot(None)).first() is not None

    # teacher_subjects: if any row exists, teachers are referenced
    from sqlalchemy import text
    teacher_subject_row = db.session.execute(
        text('SELECT 1 FROM teacher_subjects LIMIT 1')
    ).first()
    has_teacher_subject_refs = teacher_subject_row is not None

    if any([has_class_refs, has_schedule_refs, has_absence_refs, has_user_refs, has_teacher_subject_refs]):
        return jsonify({
            'success': False,
            'message': 'Cannot reset teachers because some are referenced by classes, users, timetables, absences, or subjects.'
        }), 400

    try:
        # Delete all teachers
        Teacher.query.delete()
        db.session.commit()

        # Reset ID sequence for teachers
        db.session.execute(text("""
            SELECT setval(pg_get_serial_sequence('teachers', 'id'), 1, false)
        """))
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'All teachers have been deleted and IDs reset (no references were found).'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error resetting teachers: {str(e)}'
        }), 500


@app.route('/api/teachers/<int:teacher_id>/subjects', methods=['GET', 'PUT'])
@login_required
def teacher_subjects_endpoint(teacher_id):
    """Get or update subjects for a teacher."""
    teacher = Teacher.query.get_or_404(teacher_id)
    
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'teacher_id': teacher_id,
            'subjects': [s.to_dict() for s in teacher.subjects]
        })
    
    elif request.method == 'PUT':
        data = request.get_json()
        subject_ids = data.get('subject_ids', [])
        
        # Update teacher subjects
        subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all()
        teacher.subjects = subjects
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Teacher subjects updated successfully',
            'subjects': [s.to_dict() for s in teacher.subjects]
        })


@app.route('/api/teachers/<int:teacher_id>', methods=['PUT', 'DELETE'])
@login_required
def teacher_detail(teacher_id):
    """Update or delete a specific teacher."""
    teacher = Teacher.query.get_or_404(teacher_id)
    
    if request.method == 'PUT':
        data = request.get_json()
        teacher.name = data.get('name', teacher.name)
        is_class_teacher = data.get('is_class_teacher', teacher.is_class_teacher)
        class_id = data.get('class_id')
        subject_ids = data.get('subject_ids')
        
        # Handle class teacher assignment
        if is_class_teacher and class_id:
            class_obj = Class.query.get(class_id)
            if not class_obj:
                return jsonify({
                    'success': False,
                    'message': f'Class with ID {class_id} not found'
                }), 400
            # Check if class already has a different class teacher
            if class_obj.class_teacher_id and class_obj.class_teacher_id != teacher_id:
                existing_teacher = Teacher.query.get(class_obj.class_teacher_id)
                return jsonify({
                    'success': False,
                    'message': f'Class {class_obj.name} already has a class teacher: {existing_teacher.name if existing_teacher else "Unknown"}'
                }), 400
            class_obj.class_teacher_id = teacher_id
        elif not is_class_teacher:
            # If not class teacher, remove from any class
            classes_with_this_teacher = Class.query.filter_by(class_teacher_id=teacher_id).all()
            for cls in classes_with_this_teacher:
                cls.class_teacher_id = None
        
        teacher.is_class_teacher = is_class_teacher
        teacher.is_leisure = False  # Always False now
        
        # Update subjects if provided
        if subject_ids is not None:
            subjects = Subject.query.filter(Subject.id.in_(subject_ids)).all()
            teacher.subjects = subjects
        
        db.session.commit()
        
        response_data = {
            'success': True,
            'message': 'Teacher updated successfully.',
            'teacher': teacher.to_dict()
        }
        if is_class_teacher and class_id:
            class_obj = Class.query.get(class_id)
            if class_obj:
                response_data['class_id'] = class_obj.id
        
        return jsonify(response_data)
    
    elif request.method == 'DELETE':
        teacher_name = teacher.name
        
        # Delete associated user account if exists
        associated_user = User.query.filter_by(teacher_id=teacher_id).first()
        if associated_user:
            # Prevent deleting the current admin user
            current_user = User.query.get(session.get('user_id'))
            if current_user and current_user.id == associated_user.id:
                return jsonify({
                    'success': False,
                    'message': 'Cannot delete teacher associated with your own account. Please delete your user account first.'
                }), 400
            
            db.session.delete(associated_user)
        
        # Delete teacher (this will cascade delete schedules and absences due to cascade='all, delete-orphan')
        # Clear class teacher references
        classes_using_teacher = Class.query.filter_by(class_teacher_id=teacher_id).all()
        for class_obj in classes_using_teacher:
            class_obj.class_teacher_id = None
        
        # Clear teacher-subjects associations
        teacher.subjects = []
        db.session.flush()
        
        db.session.delete(teacher)
        db.session.commit()
        
        message = f'Teacher {teacher_name} deleted successfully.'
        if associated_user:
            message += f' Associated user account "{associated_user.username}" has also been deleted.'
        
        return jsonify({
            'success': True,
            'message': message
        })


@app.route('/api/subjects', methods=['GET', 'POST'])
def subjects():
    """Get all subjects or create a new subject."""
    if request.method == 'POST':
        # POST requires authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
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


@app.route('/api/subjects/reset', methods=['POST'])
@login_required
def reset_subjects():
    """Reset subjects table (delete all and restart IDs) if nothing references them."""
    # Only admin can do this
    admin_user = User.query.get(session['user_id'])
    if not admin_user or not admin_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    # Check references from schedules
    has_schedule_refs = Schedule.query.filter(Schedule.subject_id.isnot(None)).first() is not None

    # Check references from teachers-subjects many-to-many
    # If any subject has teachers, it is being referenced
    has_teacher_refs = (
        db.session.query(Subject)
        .join(Subject.teachers)
        .first()
        is not None
    )

    if has_schedule_refs or has_teacher_refs:
        return jsonify({
            'success': False,
            'message': 'Cannot reset subjects because some are referenced by timetables or teachers.'
        }), 400

    # Safe to delete all and reset identity
    # Use DELETE instead of TRUNCATE for better compatibility
    from sqlalchemy import text

    try:
        # Delete all subjects (teacher_subjects should already be empty based on our check)
        Subject.query.delete()
        db.session.commit()
        
        # Reset the sequence to start from 1
        # Use a single query that finds and resets the sequence
        # Set to 1 with false means next value will be 1 (not 2)
        db.session.execute(text("""
            SELECT setval(pg_get_serial_sequence('subjects', 'id'), 1, false)
        """))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error resetting subjects: {str(e)}'
        }), 500

    return jsonify({
        'success': True,
        'message': 'All subjects have been deleted and IDs reset (no references were found).'
        })


@app.route('/api/subjects/<int:subject_id>', methods=['PUT', 'DELETE'])
@login_required
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
    if request.method == 'POST':
        # POST requires authentication
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
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


@app.route('/api/classes/reset', methods=['POST'])
@login_required
def reset_classes():
    """Reset classes table (delete all and restart IDs) if nothing references them."""
    # Only admin can do this
    admin_user = User.query.get(session['user_id'])
    if not admin_user or not admin_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403

    # Check references: schedules reference classes via class_id
    has_schedule_refs = Schedule.query.filter(Schedule.class_id.isnot(None)).first() is not None

    if has_schedule_refs:
        return jsonify({
            'success': False,
            'message': 'Cannot reset classes because some are referenced by timetables.'
        }), 400

    # Safe to delete all and reset identity
    from sqlalchemy import text

    try:
        # Delete all classes
        Class.query.delete()
        db.session.commit()

        # Reset the sequence to start from 1
        db.session.execute(text("""
            SELECT setval(pg_get_serial_sequence('classes', 'id'), 1, false)
        """))
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'All classes have been deleted and IDs reset (no references were found).'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error resetting classes: {str(e)}'
        }), 500


@app.route('/api/class-schedules', methods=['GET'])
@login_required
def get_class_schedules():
    """Get all class schedules showing which teacher teaches which subject for each class."""
    admin_user = User.query.get(session['user_id'])
    if not admin_user or not admin_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    # Get all classes
    classes = Class.query.all()
    schedules = Schedule.query.all()
    teachers = Teacher.query.all()
    subjects = Subject.query.all()
    
    # Create lookup maps
    teacher_map = {t.id: t.name for t in teachers}
    subject_map = {s.id: s.name for s in subjects}
    
    # Find Library and Games subjects to mark them as no-teacher subjects
    library_subject = Subject.query.filter(func.lower(Subject.name) == 'library').first()
    games_subject = Subject.query.filter(func.lower(Subject.name) == 'games').first()
    no_teacher_subject_ids = set()
    if library_subject:
        no_teacher_subject_ids.add(library_subject.id)
    if games_subject:
        no_teacher_subject_ids.add(games_subject.id)
    
    # Build class schedule data
    class_schedules = []
    for class_obj in classes:
        # Get unique subject-teacher assignments for this class
        # Each subject should have only ONE teacher (group by subject_id only, not subject_id+teacher_id)
        subject_teacher_map = {}  # {subject_id: teacher_id}
        
        # For 8th/9th grade: Track if Library or Games appears (they alternate, so show as one entry)
        class_grade = class_obj.grade if hasattr(class_obj, 'grade') else None
        has_library = False
        has_games = False
        
        for schedule in schedules:
            if schedule.class_id == class_obj.id:
                subject_id = schedule.subject_id
                
                # For 8th/9th grade: Track Library/Games separately
                if class_grade in [8, 9]:
                    if subject_id == (library_subject.id if library_subject else None):
                        has_library = True
                    elif subject_id == (games_subject.id if games_subject else None):
                        has_games = True
                    # Skip adding Library/Games to subject_teacher_map for now
                    if subject_id in no_teacher_subject_ids:
                        continue
                
                # If subject already seen, keep the first teacher assigned
                if subject_id not in subject_teacher_map:
                    subject_teacher_map[subject_id] = schedule.teacher_id
        
        # Build the list of subjects with their teachers
        subjects_list = []
        for subject_id, teacher_id in subject_teacher_map.items():
            subject_name = subject_map.get(subject_id, 'Unknown')
            # Library and Games don't have teachers
            if subject_id in no_teacher_subject_ids:
                teacher_name = 'No teacher'
            else:
                teacher_name = teacher_map.get(teacher_id, 'Unknown')
            
            subjects_list.append({
                'subject_id': subject_id,
                'subject_name': subject_name,
                'teacher_id': teacher_id,
                'teacher_name': teacher_name
            })
        
        # For 8th/9th grade: Add Library/Games as a single combined entry
        if class_grade in [8, 9]:
            if has_library or has_games:
                # Show as "Library/Games" since they alternate on different days
                subjects_list.append({
                    'subject_id': library_subject.id if library_subject else (games_subject.id if games_subject else None),
                    'subject_name': 'Library/Games',
                    'teacher_id': None,
                    'teacher_name': 'No teacher'
                })
        
        # Sort subjects by name for consistent display
        subjects_list.sort(key=lambda x: x['subject_name'])
        
        class_schedules.append({
            'class_id': class_obj.id,
            'class_name': class_obj.name,
            'subjects': subjects_list
        })
    
    return jsonify({
        'success': True,
        'class_schedules': class_schedules
        })


@app.route('/api/classes/<int:class_id>', methods=['PUT', 'DELETE'])
@login_required
def class_detail(class_id):
    """Update or delete a specific class."""
    class_obj = Class.query.get_or_404(class_id)
    
    if request.method == 'PUT':
        data = request.get_json()
        class_obj.name = data.get('name', class_obj.name)
        class_obj.grade = data.get('grade', class_obj.grade)
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


@app.route('/api/teacher-update-request', methods=['POST'])
@login_required
def create_teacher_update_request():
    """Create a teacher update request (subjects and classes)."""
    user = User.query.get(session['user_id'])
    if not user or not user.teacher_id:
        return jsonify({
            'success': False,
            'message': 'No teacher profile associated with this account.'
        }), 400
    
    teacher = Teacher.query.get(user.teacher_id)
    if not teacher:
        return jsonify({
            'success': False,
            'message': 'Teacher profile not found.'
        }), 404
    
    data = request.get_json()
    subject_ids = data.get('subject_ids', [])
    class_ids = data.get('class_ids', [])
    
    # Validate that subject_ids and class_ids are arrays
    if not isinstance(subject_ids, list) or not isinstance(class_ids, list):
        return jsonify({
            'success': False,
            'message': 'subject_ids and class_ids must be arrays'
        }), 400
    
    # Check if there's already a pending request
    existing_request = TeacherUpdateRequest.query.filter_by(
        teacher_id=teacher.id,
        status='pending'
    ).first()
    
    if existing_request:
        return jsonify({
            'success': False,
            'message': 'You already have a pending update request. Please wait for admin approval or cancel the existing request.'
        }), 400
    
    import json
    # Create new request
    update_request = TeacherUpdateRequest(
        teacher_id=teacher.id,
        requested_subject_ids=json.dumps(subject_ids),
        requested_class_ids=json.dumps(class_ids),
        status='pending'
    )
    
    db.session.add(update_request)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Update request submitted successfully. Waiting for admin approval.',
        'request': update_request.to_dict()
    })


@app.route('/api/teacher-update-requests', methods=['GET'])
@login_required
def get_teacher_update_requests():
    """Get all teacher update requests (admin only) or teacher's own requests."""
    try:
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        if user.is_admin:
            # Admin sees all requests
            requests = TeacherUpdateRequest.query.order_by(TeacherUpdateRequest.created_at.desc()).all()
        else:
            # Teacher sees only their own requests
            if not user.teacher_id:
                return jsonify({
                    'success': False,
                    'message': 'No teacher profile associated with this account.'
                }), 400
            requests = TeacherUpdateRequest.query.filter_by(
                teacher_id=user.teacher_id
            ).order_by(TeacherUpdateRequest.created_at.desc()).all()
        
        # Convert to dict with error handling
        requests_list = []
        for r in requests:
            try:
                requests_list.append(r.to_dict())
            except Exception as e:
                print(f"Error converting request {r.id} to dict: {e}")
                # Return basic info even if to_dict fails
                requests_list.append({
                    'id': r.id,
                    'teacher_id': r.teacher_id,
                    'teacher_name': r.teacher.name if r.teacher else 'Unknown',
                    'status': r.status,
                    'requested_subject_ids': [],
                    'requested_class_ids': [],
                    'admin_notes': r.admin_notes,
                    'created_at': r.created_at.isoformat() if r.created_at else None
                })
        
        return jsonify({
            'success': True,
            'requests': requests_list
        })
    except Exception as e:
        print(f"Error in get_teacher_update_requests: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error loading requests: {str(e)}'
        }), 500


@app.route('/api/teacher-update-requests/<int:request_id>/approve', methods=['POST'])
@login_required
def approve_teacher_update_request(request_id):
    """Approve a teacher update request (admin only)."""
    admin_user = User.query.get(session['user_id'])
    if not admin_user or not admin_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    update_request = TeacherUpdateRequest.query.get_or_404(request_id)
    if update_request.status != 'pending':
        return jsonify({
            'success': False,
            'message': f'Request is already {update_request.status}'
        }), 400
    
    teacher = Teacher.query.get(update_request.teacher_id)
    if not teacher:
        return jsonify({
            'success': False,
            'message': 'Teacher not found'
        }), 404
    
    import json
    data = request.get_json() or {}
    admin_notes = data.get('admin_notes', '')
    
    try:
        # Parse requested IDs
        requested_subject_ids = json.loads(update_request.requested_subject_ids)
        requested_class_ids = json.loads(update_request.requested_class_ids)
        
        # Update teacher subjects
        subjects = Subject.query.filter(Subject.id.in_(requested_subject_ids)).all()
        teacher.subjects = subjects
        
        # Update schedules - remove old schedules for classes teacher no longer teaches
        requested_class_ids_set = set(requested_class_ids)
        
        # Delete schedules for classes teacher no longer teaches
        # This ensures that if a teacher is removed from teaching a class,
        # all their schedules for that class are removed
        all_teacher_schedules = Schedule.query.filter(
            Schedule.teacher_id == teacher.id
        ).all()
        
        for schedule in all_teacher_schedules:
            if schedule.class_id not in requested_class_ids_set:
                db.session.delete(schedule)
        
        # Note: We don't automatically create new schedules for new classes
        # Admin will need to generate/update schedules separately using the schedule generation feature
        
        # Update request status
        update_request.status = 'approved'
        update_request.admin_notes = admin_notes
        update_request.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Teacher update request approved. Subjects updated. Schedules for removed classes have been deleted.',
            'request': update_request.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error approving request: {str(e)}'
        }), 500


@app.route('/api/teacher-update-requests/<int:request_id>/reject', methods=['POST'])
@login_required
def reject_teacher_update_request(request_id):
    """Reject a teacher update request (admin only)."""
    admin_user = User.query.get(session['user_id'])
    if not admin_user or not admin_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin access required'}), 403
    
    update_request = TeacherUpdateRequest.query.get_or_404(request_id)
    if update_request.status != 'pending':
        return jsonify({
            'success': False,
            'message': f'Request is already {update_request.status}'
        }), 400
    
    data = request.get_json() or {}
    admin_notes = data.get('admin_notes', '')
    
    update_request.status = 'rejected'
    update_request.admin_notes = admin_notes
    update_request.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Teacher update request rejected.',
        'request': update_request.to_dict()
    })


@app.route('/api/teacher-update-requests/<int:request_id>', methods=['DELETE'])
@login_required
def delete_teacher_update_request(request_id):
    """Delete a teacher update request (teacher can delete own pending requests, admin can delete any)."""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    update_request = TeacherUpdateRequest.query.get_or_404(request_id)
    
    # Check permissions: teacher can only delete their own pending requests, admin can delete any
    if not user.is_admin:
        if not user.teacher_id or update_request.teacher_id != user.teacher_id:
            return jsonify({
                'success': False,
                'message': 'You can only delete your own requests'
            }), 403
        
        if update_request.status != 'pending':
            return jsonify({
                'success': False,
                'message': 'You can only delete pending requests'
            }), 400
    
    try:
        db.session.delete(update_request)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Request deleted successfully.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error deleting request: {str(e)}'
        }), 500


@app.route('/api/my-timetable', methods=['GET'])
@login_required
def my_timetable():
    """
    Get timetable for the currently logged-in user (teacher).
    Query params:
        date: Optional date in YYYY-MM-DD format (defaults to today)
    """
    user = User.query.get(session['user_id'])
    if not user or not user.teacher_id:
        return jsonify({
            'success': False,
            'message': 'No teacher associated with this account. Please contact admin.'
        }), 400
    
    # Get date from query parameter or use today
    date_str = request.args.get('date', date.today().isoformat())
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({
            'success': False,
            'message': 'Invalid date format. Use YYYY-MM-DD.'
        }), 400
    
    teacher = Teacher.query.get(user.teacher_id)
    if not teacher:
        return jsonify({
            'success': False,
            'message': 'Teacher profile not found'
        }), 404
    
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
        teacher_id=user.teacher_id,
        day=day_of_week
    ).order_by(Schedule.period).all()
    
    # Format schedule data
    timetable = []
    for schedule in schedules:
        class_obj = Class.query.get(schedule.class_id)
        subject_obj = Subject.query.get(schedule.subject_id)
        
        timetable.append({
            'period': schedule.period,
            'class_name': class_obj.name if class_obj else 'Unknown',
            'subject_name': subject_obj.name if subject_obj else 'Unknown',
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
    # Port can be configured via PORT environment variable, defaults to 5001
    port = int(os.getenv('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)

