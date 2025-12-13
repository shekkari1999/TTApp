# TTApp - School Timetable Management System

A web-based application for managing school timetables, teacher schedules, and handling substitutions for absent teachers.

## Features

- 🎯 **Generate Initial Schedule** - Create schedules for all teachers based on classes, subjects, and periods
- 👁️ **View Absent Teachers** - See who's absent and get substitution suggestions
- ⚙️ **Dynamic Configuration** - Configure number of classes, subjects, and periods
- 📊 **Smart Substitution** - Automatically suggests available substitutes based on schedules
- 🎨 **Modern UI** - Clean, responsive interface

## Tech Stack

- **Backend:** Flask (Python)
- **Database:** PostgreSQL (ready for pgvector/AI integration)
- **ORM:** SQLAlchemy
- **Frontend:** HTML, CSS, JavaScript (vanilla)

## Prerequisites

- Python 3.12+
- PostgreSQL database
- `uv` package manager (or pip)

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd TTApp
   ```

2. **Create and activate virtual environment:**
   ```powershell
   # Using uv
   uv venv
   .\.venv\Scripts\Activate.ps1
   
   # Or using venv
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   uv pip install -e .
   # Or
   pip install -e .
   ```

4. **Set up PostgreSQL database:**
   ```sql
   CREATE DATABASE ttapp;
   ```

5. **Configure environment variables:**
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and update:
   # DATABASE_URL=postgresql://username:password@localhost:5432/ttapp
   # SECRET_KEY=your-secret-key-here
   ```

## Running the Application

1. **Activate virtual environment:**
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

2. **Run the Flask app:**
   ```bash
   python app.py
   ```

3. **Open in browser:**
   Navigate to `http://localhost:5000`

## Initial Setup

Before generating schedules, you need to add some data:

### Option 1: Using API (via Python script or Postman)

```python
import requests

# Add teachers
requests.post('http://localhost:5000/api/teachers', json={
    'name': 'John Doe',
    'is_class_teacher': True,
    'is_leisure': False
})

# Add subjects
requests.post('http://localhost:5000/api/subjects', json={
    'name': 'Mathematics'
})

# Add classes
requests.post('http://localhost:5000/api/classes', json={
    'name': 'Class 1',
    'class_teacher_id': 1
})
```

### Option 2: Using SQL (direct database access)

```sql
-- Add teachers
INSERT INTO teachers (name, is_class_teacher, is_leisure) VALUES
('John Doe', true, false),
('Jane Smith', true, false),
('Bob Johnson', false, false);

-- Add subjects
INSERT INTO subjects (name) VALUES
('Mathematics'),
('Science'),
('English');

-- Add classes
INSERT INTO classes (name, class_teacher_id) VALUES
('Class 1', 1),
('Class 2', 2);
```

## Usage

1. **Generate Initial Schedule:**
   - Click "Generate Initial Schedule" button
   - Configure number of classes, subjects, and periods
   - The system will create a schedule for all teachers

2. **View Absent Teachers:**
   - Click "View Absent Teachers & Substitutions"
   - Select a date
   - See who's absent and available substitutes

3. **Mark Teacher as Absent:**
   - Use the API endpoint:
   ```bash
   POST /api/absent-teachers
   {
     "teacher_id": 1,
     "date": "2024-12-13"
   }
   ```

## Project Structure

```
TTApp/
├── app.py                 # Main Flask application
├── models.py              # Database models
├── main.py                # Entry point
├── templates/
│   └── index.html         # Main UI template
├── static/
│   ├── style.css          # Styling
│   └── script.js          # Frontend JavaScript
├── PROGRESS.md            # Development progress log
├── pyproject.toml         # Project dependencies
└── README.md              # This file
```

## API Endpoints

- `GET /` - Main page
- `POST /api/generate-schedule` - Generate initial schedule
- `GET /api/absent-teachers?date=YYYY-MM-DD` - View absent teachers
- `POST /api/absent-teachers` - Mark teacher as absent
- `GET /api/teachers` - List all teachers
- `POST /api/teachers` - Create teacher
- `GET /api/subjects` - List all subjects
- `POST /api/subjects` - Create subject
- `GET /api/classes` - List all classes
- `POST /api/classes` - Create class

## Future Enhancements

- AI-powered schedule optimization (using pgvector)
- Individual teacher schedule view
- Manual schedule editing
- Schedule export (PDF/Excel)
- User authentication
- Reports and analytics

## Development

See `PROGRESS.md` for detailed development progress and notes.

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

