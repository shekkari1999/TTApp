"""
Database Models for TTApp (Timetable Management System)

This module defines all database models using SQLAlchemy ORM.
Models include: Teachers, Subjects, Classes, Schedules, and Absences.
"""

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Initialize SQLAlchemy instance (will be initialized in app.py)
db = SQLAlchemy()


class User(db.Model):
    """
    User model - stores admin user accounts for authentication.
    
    Attributes:
        id: Primary key
        username: Unique username for login
        email: User's email address
        password_hash: Hashed password (never store plain passwords)
        is_admin: Boolean indicating if user has admin privileges
        created_at: Timestamp when record was created
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)  # Nullable to allow admin-created accounts without email
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable to allow admin-created accounts without password
    is_admin = db.Column(db.Boolean, default=False, nullable=False)  # Changed default to False
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)  # Link to teacher if regular user
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship
    teacher = db.relationship('Teacher', backref='user', lazy=True)
    
    def set_password(self, password):
        """Hash and set the password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        """Convert user object to dictionary (excluding sensitive data)."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'status': self.status,
            'teacher_id': self.teacher_id
        }


# Association table for many-to-many relationship between Teacher and Subject
teacher_subjects = db.Table('teacher_subjects',
    db.Column('teacher_id', db.Integer, db.ForeignKey('teachers.id'), primary_key=True),
    db.Column('subject_id', db.Integer, db.ForeignKey('subjects.id'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow, nullable=False)
)


class Teacher(db.Model):
    """
    Teacher model - stores information about teachers in the school.
    
    Attributes:
        id: Primary key
        name: Teacher's full name
        is_class_teacher: Boolean indicating if teacher is a class teacher
        is_leisure: Boolean indicating if teacher is on leisure (not assigned to classes)
        created_at: Timestamp when record was created
    """
    __tablename__ = 'teachers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    is_class_teacher = db.Column(db.Boolean, default=False, nullable=False)
    is_leisure = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    schedules = db.relationship('Schedule', backref='teacher', lazy=True, cascade='all, delete-orphan')
    # absences: absences where this teacher is the absent teacher (not the substitute)
    absences = db.relationship('Absence', foreign_keys='Absence.teacher_id', backref='absent_teacher', lazy=True, cascade='all, delete-orphan')
    # substitutions: absences where this teacher is the substitute
    substitutions = db.relationship('Absence', foreign_keys='Absence.substitute_teacher_id', backref='substitute_teacher', lazy=True)
    # subjects: many-to-many relationship with subjects
    subjects = db.relationship('Subject', secondary=teacher_subjects, lazy='subquery', backref=db.backref('teachers', lazy=True))
    
    def __repr__(self):
        return f'<Teacher {self.name}>'
    
    def to_dict(self):
        """Convert teacher object to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'is_class_teacher': self.is_class_teacher,
            'is_leisure': self.is_leisure,
            'subject_ids': [s.id for s in self.subjects] if self.subjects else []
        }


class Subject(db.Model):
    """
    Subject model - stores information about subjects taught in the school.
    
    Attributes:
        id: Primary key
        name: Name of the subject
        created_at: Timestamp when record was created
    """
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    schedules = db.relationship('Schedule', backref='subject', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Subject {self.name}>'
    
    def to_dict(self):
        """Convert subject object to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name
        }


class Class(db.Model):
    """
    Class model - stores information about classes in the school.
    
    Attributes:
        id: Primary key
        name: Name/identifier of the class (e.g., "Class 1", "Grade 5A")
        class_teacher_id: Foreign key to the teacher assigned as class teacher
        created_at: Timestamp when record was created
    """
    __tablename__ = 'classes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    class_teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    schedules = db.relationship('Schedule', backref='class_ref', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Class {self.name}>'
    
    def to_dict(self):
        """Convert class object to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'class_teacher_id': self.class_teacher_id
        }


class Schedule(db.Model):
    """
    Schedule model - stores the timetable/schedule for teachers and classes.
    
    Attributes:
        id: Primary key
        teacher_id: Foreign key to the teacher
        class_id: Foreign key to the class
        subject_id: Foreign key to the subject
        day: Day of the week (0=Monday, 6=Sunday)
        period: Period number in the day (1, 2, 3, etc.)
        date: Specific date for the schedule (for daily schedules)
        created_at: Timestamp when record was created
    """
    __tablename__ = 'schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    day = db.Column(db.Integer, nullable=False)  # 0=Monday, 6=Sunday
    period = db.Column(db.Integer, nullable=False)  # Period number (1, 2, 3, ...)
    date = db.Column(db.Date, nullable=True)  # Optional: specific date
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Schedule Teacher:{self.teacher_id} Class:{self.class_id} Day:{self.day} Period:{self.period}>'
    
    def to_dict(self):
        """Convert schedule object to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'class_id': self.class_id,
            'subject_id': self.subject_id,
            'day': self.day,
            'period': self.period,
            'date': self.date.isoformat() if self.date else None
        }


class Absence(db.Model):
    """
    Absence model - tracks teacher absences for substitution purposes.
    
    Attributes:
        id: Primary key
        teacher_id: Foreign key to the absent teacher
        date: Date of absence
        is_substituted: Boolean indicating if substitution has been arranged
        substitute_teacher_id: Foreign key to the substitute teacher (if assigned)
        created_at: Timestamp when record was created
    """
    __tablename__ = 'absences'
    
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    is_substituted = db.Column(db.Boolean, default=False, nullable=False)
    substitute_teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Absence Teacher:{self.teacher_id} Date:{self.date}>'
    
    def to_dict(self):
        """Convert absence object to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'date': self.date.isoformat(),
            'is_substituted': self.is_substituted,
            'substitute_teacher_id': self.substitute_teacher_id
        }

