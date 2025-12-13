# Quick Setup Guide

## Step 1: Install Dependencies

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install packages
uv pip install -e .
```

## Step 2: Set Up PostgreSQL

1. **Install PostgreSQL** (if not already installed)
   - Download from: https://www.postgresql.org/download/

2. **Create Database:**
   ```sql
   CREATE DATABASE ttapp;
   ```

3. **Note your connection details:**
   - Username: (your PostgreSQL username)
   - Password: (your PostgreSQL password)
   - Host: localhost (usually)
   - Port: 5432 (default)
   - Database: ttapp

## Step 3: Configure Environment

1. **Create `.env` file** in the project root:
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/ttapp
   SECRET_KEY=your-secret-key-here-change-in-production
   ```

2. **Replace:**
   - `username` with your PostgreSQL username
   - `password` with your PostgreSQL password
   - `your-secret-key-here` with a random secret key

## Step 4: Initialize Database

```powershell
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

Or run the app once and it will create tables automatically.

## Step 5: Add Sample Data

You can add sample data using Python:

```python
from app import app, db
from models import Teacher, Subject, Class

with app.app_context():
    # Add teachers
    teachers = [
        Teacher(name='John Doe', is_class_teacher=True, is_leisure=False),
        Teacher(name='Jane Smith', is_class_teacher=True, is_leisure=False),
        Teacher(name='Bob Johnson', is_class_teacher=False, is_leisure=False),
        Teacher(name='Alice Brown', is_class_teacher=False, is_leisure=True),
    ]
    for teacher in teachers:
        db.session.add(teacher)
    
    # Add subjects
    subjects = [
        Subject(name='Mathematics'),
        Subject(name='Science'),
        Subject(name='English'),
        Subject(name='History'),
        Subject(name='Geography'),
        Subject(name='Art'),
        Subject(name='Physical Education'),
    ]
    for subject in subjects:
        db.session.add(subject)
    
    # Add classes
    classes = [
        Class(name='Class 1', class_teacher_id=1),
        Class(name='Class 2', class_teacher_id=2),
        Class(name='Class 3', class_teacher_id=1),
        Class(name='Class 4', class_teacher_id=2),
        Class(name='Class 5', class_teacher_id=1),
    ]
    for class_obj in classes:
        db.session.add(class_obj)
    
    db.session.commit()
    print("Sample data added successfully!")
```

## Step 6: Run the Application

```powershell
python app.py
```

Or:

```powershell
python main.py
```

Then open: `http://localhost:5000`

## Troubleshooting

### Database Connection Error
- Check PostgreSQL is running
- Verify DATABASE_URL in `.env` is correct
- Ensure database `ttapp` exists

### Import Errors
- Make sure virtual environment is activated
- Run `uv pip install -e .` again

### Port Already in Use
- Change port in `app.py`: `app.run(port=5001)`

